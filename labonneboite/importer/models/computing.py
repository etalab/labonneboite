# coding: utf8
import datetime

from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Boolean

from labonneboite.importer import settings
from labonneboite.common.database import Base
from labonneboite.common.models.base import CRUDMixin


class Dpae(CRUDMixin, Base):
    __tablename__ = settings.DPAE_TABLE

    _id = Column('id', BigInteger, primary_key=True)
    siret = Column(String(191))
    hiring_date = Column(DateTime, default=datetime.datetime.utcnow)
    zipcode = Column(String(8))
    contract_type = Column(Integer)
    departement = Column(String(8))
    contract_duration = Column(Integer)
    iiann = Column(String(191))
    age_group = Column('tranche_age', String(191))
    handicap_label = Column(String(191))

    def __str__(self):
        return '%s %s' % (self.siret, self.hiring_date)


class Office(CRUDMixin, Base):
    """
    raw importer table including all 10M offices
    """
    __tablename__ = settings.OFFICE_TABLE
    siret = Column(String(14), primary_key=True)
    company_name = Column('raisonsociale', String(191))
    office_name = Column('enseigne', String(191))
    naf = Column('codenaf', String(8))
    street_number = Column('numerorue', String(191))
    street_name = Column('libellerue', String(191))
    city_code = Column('codecommune', String(191))
    zipcode = Column('codepostal', String(8))
    email = Column(String(191))
    tel = Column(String(191))
    website1 = Column(String(191))
    website2 = Column(String(191))

    departement = Column(String(8))
    headcount = Column('trancheeffectif', String(2))


class Geolocation(CRUDMixin, Base):
    """
    cache each full_address <=> coordinates(longitude, latitude) match
    managed by geocoding process
    """
    __tablename__ = "geolocations"
    full_address = Column(String(191), primary_key=True)
    x = Column('coordinates_x', Float)  # longitude
    y = Column('coordinates_y', Float)  # latitude


class ExportableOffice(CRUDMixin, Base):
    """
    importer table including selected offices (~500K)
    ready to be exported to staging and production
    -
    note that this is actually a duplicate of the Office model
    in common/models/office.py
    TOFIX somehow eliminate this confusing code duplication
    """
    __tablename__ = settings.EXPORT_ETABLISSEMENT_TABLE
    siret = Column(String(14), primary_key=True)
    company_name = Column('raisonsociale', String(191))
    office_name = Column('enseigne', String(191))
    naf = Column('codenaf', String(8))
    street_number = Column('numerorue', String(191))
    street_name = Column('libellerue', String(191))
    city_code = Column('codecommune', String(191))
    zipcode = Column('codepostal', String(8))
    email = Column(String(191))
    tel = Column(String(191))
    website = Column(String(191))
    flag_alternance = Column(Boolean, default=False, nullable=False)
    flag_junior = Column(Boolean, default=False, nullable=False)
    flag_senior = Column(Boolean, default=False, nullable=False)
    flag_handicap = Column(Boolean, default=False, nullable=False)
    has_multi_geolocations = Column(Boolean, default=False, nullable=False)

    departement = Column(String(8))
    headcount = Column('trancheeffectif', String(2))
    score = Column(Integer)
    x = Column('coordinates_x', Float)  # longitude
    y = Column('coordinates_y', Float)  # latitude


class ImportTask(CRUDMixin, Base):
    __tablename__ = "import_tasks"

    # Import state
    FILE_READ = 1
    FILE_IMPORTED = 2
    NO_CHANGE = 3

    # Import type
    DPAE = 1
    ETABLISSEMENT = 2

    _id = Column('id', BigInteger, primary_key=True)
    filename = Column(String(191))
    state = Column(Integer)
    import_type = Column(Integer)
    created_date = Column(DateTime, default=datetime.datetime.utcnow)

    @classmethod
    def is_last_import_dpae(clazz):
        return clazz.query.order_by(clazz.created_date.desc()).first().import_type == ImportTask.DPAE


class DpaeStatistics(CRUDMixin, Base):
    __tablename__ = "dpae_statistics"

    _id = Column('id', BigInteger, primary_key=True)
    last_import = Column(DateTime, default=datetime.datetime.utcnow)
    most_recent_data_date = Column(DateTime, default=datetime.datetime.utcnow)

    @classmethod
    def get_most_recent_data_date(clazz):
        try:
            return clazz.query.order_by(clazz.most_recent_data_date.desc()).first().most_recent_data_date
        except AttributeError:
            # if there was no import of dpae thus far, return the date for which
            # we don't want to import dpae before that date
            return settings.MOST_RECENT_DPAE_DATE
