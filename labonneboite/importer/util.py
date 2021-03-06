import os
import gzip
import bz2
import re
import subprocess
from datetime import datetime

import MySQLdb as mdb

from labonneboite.importer import settings as importer_settings
from labonneboite.conf import settings
from labonneboite.importer.models.computing import ImportTask
from labonneboite.common.database import DATABASE
from labonneboite.common import encoding as encoding_util

import logging
logger = logging.getLogger('main')

TRANCHE_AGE_SENIOR = "51-99"
TRANCHE_AGE_JUNIOR = "00-25"
TRANCHE_AGE_MIDDLE = "26-50"

OFFICE_FLAGS = ['flag_alternance', 'flag_junior', 'flag_senior', 'flag_handicap']


class DepartementException(Exception):
    pass


class TooFewFieldsException(Exception):
    pass


def create_cursor():
    con = mdb.connect('localhost', DATABASE['USER'], DATABASE['PASSWORD'], DATABASE['NAME'],
        use_unicode=True, charset="utf8")
    cur = con.cursor()
    return con, cur


def check_for_updates(input_folder):
    """
    do we have a new file we haven't processed yet in the input folder?
    """
    new_files = []
    for name in os.listdir(input_folder):
        full_name = os.path.join(input_folder, name)
        if not is_processed(full_name):
            new_files.append(full_name)
        else:
            logger.info("file %s was already processed and will thus be ignored" % full_name)
    return new_files


def back_up(backup_folder, table, name, timestamp, copy_to_remote_server=True, rename_table=False):
    timestamp_filename = '%s_backup_%s.sql.gz' % (name, timestamp)
    backup_filename = os.path.join(backup_folder, timestamp_filename)
    password_statement = "-p'%s'" % DATABASE['PASSWORD']
    logger.info("backing up %s into %s", name, backup_filename)
    if rename_table:
        table_new = table+"_new"
    else:
        table_new = table

    # sed command from https://stackoverflow.com/questions/8042723/mysqldump-can-you-change-the-name-of-the-table-youre-inserting-into
    # to rename table name on the fly,
    # useful in the case of deploy_data to allow zero downtime atomic table swap of table etablissements
    subprocess.check_call(
        """mysqldump -u %s %s %s %s | sed 's/`%s`/`%s`/g' | gzip > %s""" % (
            DATABASE['USER'],
            password_statement,
            DATABASE['NAME'],
            table,
            table,
            table_new,
            backup_filename),
        shell=True)
    
    if copy_to_remote_server:
        logger.info("copying the file to remote server")
        subprocess.check_call("scp %s %s@%s:%s " % (
            backup_filename, settings.BACKUP_USER, settings.BACKUP_SERVER, settings.BACKUP_SERVER_PATH),
            shell=True)
    logger.info("finished back up !")
    return backup_filename


def is_processed(filename):
    """
    an input file can be in different states,
    in order to track whether its contents were imported or not.
    This function lets us know whether contents were imported or not.
    """
    import_tasks = ImportTask.query.filter(
        ImportTask.filename == os.path.basename(filename),
        ImportTask.state >= ImportTask.FILE_READ).all()
    if import_tasks:
        return True
    else:
        return False


def check_runnable(filename, file_type):
    patterns = {
        'dpae': 'LBB_XDPDPA_DPAE_.*',
        'etablissements': 'LBB_EGCEMP_ENTREPRISE_.*'
    }
    base_name = os.path.basename(filename)
    return re.match(patterns[file_type], base_name) and not is_processed(base_name)


def detect_runnable_file(file_type):
    logger.info("detect runnable file for file type: %s", file_type)
    for filename in check_for_updates(importer_settings.INPUT_SOURCE_FOLDER):
        logger.info("inspecting file %s" % filename)
        if check_runnable(filename, file_type):
            logger.info("will run this file : %s" % filename)
            return filename
    logger.info("no runnable file found!")
    return None


def reduce_scores_into_table(description, create_table_filename, departements, target_table, select_fields, drop_low_scores):
    """
    Analog to a Map/Reduce operation.
    We have "etablissements" in MySQL tables for each departement.
    This step combines all etablissements into a single MySQL table, ready to be exported.

    WARNING : this drops the original target_table and repopulates it from scratch
    """
    logger.info("reducing scores %s ..." % description)
    sql_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", create_table_filename)
    init_query = open(sql_filepath, "r").read()
    if importer_settings.MYSQL_NO_PASSWORD:
        password_statement = ''
    else:
        password_statement = "-p'%s'" % DATABASE['PASSWORD']

    subprocess.check_call("""mysql -u %s %s %s -e'%s'""" % (
        DATABASE['USER'], password_statement, DATABASE['NAME'], init_query), shell=True)

    for departement in departements:
        departement_table = "etablissements_%s" % departement
        query = """insert into %s select %s from %s""" % (
            target_table, select_fields, departement_table)
        if drop_low_scores:
            query += " where score >= 50"
        try:
            subprocess.check_call("""mysql -u %s %s %s -e'%s'""" % (DATABASE['USER'], password_statement, DATABASE['NAME'], query), shell=True)
        except:
            logger.error("an error happened in reducing %s %s" % (departement, description))
            raise
    logger.info("score reduction %s finished, all data available in table %s" % (
        description, target_table))


def get_select_fields_for_main_db():
    """
    These fields should exactly match (and in the same order)
    the fields in etablissements_main_db.sql
    """
    return (
        """siret, raisonsociale, enseigne, codenaf,
        trancheeffectif, numerorue, libellerue, codepostal,
        tel, email, website, """
        + "0, 0, 0, 0, " # stand for flag_alternance, flag_junior, flag_senior, flag_handicap
        + "codecommune, "
        + "0, 0, " # stand for coordinates_x, coordinates_y
        + "departement, score "
        )


def get_select_fields_for_backoffice():
    """
    These fields should exactly match (and in the same order)
    the fields in etablissements_backoffice_db.sql
    """
    fields = get_select_fields_for_main_db()
    fields += ", `semester-1`, `semester-2`, `semester-3`, `semester-4`, `semester-5`, `semester-6`, `semester-7`"
    fields += ", effectif, score_regr"
    return fields


def reduce_scores_for_main_db(departements):
    reduce_scores_into_table(
        description="[main_db]",
        create_table_filename="db/etablissements_main_db.sql",
        departements=departements,
        target_table=importer_settings.EXPORT_ETABLISSEMENT_TABLE,
        select_fields=get_select_fields_for_main_db(),
        drop_low_scores=True
    )


def reduce_scores_for_backoffice(departements):
    reduce_scores_into_table(
        description="[backoffice]",
        create_table_filename="db/etablissements_backoffice.sql",
        departements=departements,
        target_table=importer_settings.BACKOFFICE_ETABLISSEMENT_TABLE,
        select_fields=get_select_fields_for_backoffice(),
        drop_low_scores=False
    )


def clean_tables():
    if importer_settings.MYSQL_NO_PASSWORD:
        password_statement = ''
    else:
        password_statement = "-p'%s'" % DATABASE['PASSWORD']

    logger.info("clean all departement database tables...")
    departements = importer_settings.DEPARTEMENTS
    for departement in departements:
        departement_table = "etablissements_%s" % departement
        drop_table_query = "drop table if exists %s" % departement_table
        subprocess.check_call("""mysql -u %s %s %s -e'%s'""" % (
            DATABASE['USER'], password_statement, DATABASE['NAME'], drop_table_query), shell=True)


def extract_departement_from_zipcode(zipcode, siret):
    zipcode = zipcode.strip()
    departement = None
    if len(zipcode) in range(1, 6):
        if len(zipcode) == 1:
            departement = "0%s" % zipcode[0]
        elif len(zipcode) == 2:
            departement = zipcode
        elif len(zipcode) == 4:
            departement = "0%s" % zipcode[0]
        elif len(zipcode) == 5:
            departement = zipcode[:2]
        else:
            raise DepartementException("length ok but departement not recognized for siret %s %s" % (siret, zipcode))
    else:
        raise DepartementException("departement not recognized for siret %s %s" % (siret, zipcode))
    return departement


def get_fields_from_csv_line(line):
    # get rid of invisible space characters (\xc2) if present
    line = line.strip().replace('\xc2', '')
    # ignore enclosing quotes if present
    if (line[0] in ["'", '"']):
        line = line[1:]
    if (line[-1] in ["'", '"']):
        line = line[:-1]
    # split using delimiter special character \xa5
    fields = [encoding_util.sanitize_string(f) for f in line.split('\xa5')]
    return fields


def parse_dpae_line(line):
    fields = get_fields_from_csv_line(line)
    required_fields = 24
    if len(fields) != required_fields:  # an assert statement here does not work from nosetests
        msg = ("found %s fields instead of %s in line: %s" % (
            len(fields), required_fields, line
        ))
        logger.error(msg)
        if len(fields) < required_fields:
            raise TooFewFieldsException
        else:
            raise Exception("found a row with wrong number of columns [%s]" % msg)

    siret = fields[0]
    hiring_date_raw = fields[7]
    hiring_date = datetime.strptime(hiring_date_raw, "%Y-%m-%d %H:%M:%S")

    try:
        zipcode = int(fields[3])
    except ValueError:
        zipcode = None

    departement = extract_departement_from_zipcode(str(zipcode), siret)

    try:
        contract_type = int(fields[8])
    except ValueError:
        contract_type = None

    try:
        contract_duration = int(fields[20])
    except ValueError:
        contract_duration = None

    iiann = fields[21]

    def remove_exotic_characters(text):
        return ''.join(i for i in text if ord(i)<128)

    choices = {
        "- de 26 ans": TRANCHE_AGE_JUNIOR,
        "de 26 ans  50 ans": TRANCHE_AGE_MIDDLE,
        "+ de 50 ans": TRANCHE_AGE_SENIOR
    }
    
    try:
        tranche_age = choices[remove_exotic_characters(fields[22])]
    except KeyError:
        raise Exception("unknown tranche_age %s" % fields[22])

    handicap_label = fields[23]

    return siret, hiring_date, zipcode, contract_type, departement, contract_duration, iiann, tranche_age, handicap_label


def get_file_extension(filename):
    _, file_extension = os.path.splitext(filename)
    return file_extension


def get_open_file(filename):
    file_extension = get_file_extension(filename)
    if file_extension == ".gz":
        open_file = gzip.open
    elif file_extension == ".bz2":
        open_file = bz2.BZ2File
    elif file_extension == ".csv":
        open_file = open
    else:
        raise "unknown file extension"
    return open_file


def get_reader(filename):
    open_file = get_open_file(filename)
    return open_file(filename, "r")
