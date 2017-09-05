DROP TABLE if exists etablissements_backoffice;

CREATE TABLE etablissements_backoffice (
  siret varchar(191),
  raisonsociale varchar(191) DEFAULT NULL,
  enseigne varchar(191) DEFAULT NULL,
  codenaf varchar(191) DEFAULT NULL,
  trancheeffectif varchar(191) DEFAULT NULL,
  numerorue varchar(191) DEFAULT NULL,
  libellerue varchar(191) DEFAULT NULL,
  codepostal varchar(8) DEFAULT NULL,
  tel varchar(191) DEFAULT NULL,
  email varchar(191) DEFAULT NULL,
  website varchar(191) DEFAULT NULL,
  flag_alternance tinyint(1) NOT NULL,
  flag_junior tinyint(1) NOT NULL,
  flag_senior tinyint(1) NOT NULL,
  flag_handicap tinyint(1) NOT NULL,
  has_multi_geolocations tinyint(1) NOT NULL,
  codecommune varchar(191) DEFAULT NULL,
  coordinates_x double DEFAULT NULL,
  coordinates_y double DEFAULT NULL,
  departement varchar(8) DEFAULT NULL,
  score int(11) DEFAULT NULL,
  `semester-1` double DEFAULT NULL,
  `semester-2` double DEFAULT NULL,
  `semester-3` double DEFAULT NULL,
  `semester-4` double DEFAULT NULL,
  `semester-5` double DEFAULT NULL,
  `semester-6` double DEFAULT NULL,
  `semester-7` double DEFAULT NULL,
  `effectif` double DEFAULT NULL,
  `score_regr` float DEFAULT NULL,
  PRIMARY KEY (siret),
  KEY dept_i (departement)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
