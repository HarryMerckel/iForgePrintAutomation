-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Server version:               10.4.6-MariaDB - mariadb.org binary distribution
-- Server OS:                    Win64
-- HeidiSQL Version:             9.5.0.5196
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;


-- Dumping database structure for iforge print queue
CREATE DATABASE IF NOT EXISTS `iforge print queue` /*!40100 DEFAULT CHARACTER SET latin1 */;
USE `iforge print queue`;

-- Dumping structure for table iforge print queue.printers
CREATE TABLE IF NOT EXISTS `printers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` tinytext DEFAULT NULL,
  `type` tinytext DEFAULT NULL,
  `ip address` tinytext DEFAULT NULL,
  `api key` tinytext DEFAULT NULL,
  `total time printed` int(10) unsigned DEFAULT 0,
  `maintenance time` int(10) unsigned DEFAULT 0,
  `completed prints` int(10) unsigned DEFAULT 0,
  `failed prints` int(10) unsigned DEFAULT 0,
  `total filament used` float unsigned DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
-- Dumping structure for table iforge print queue.prints
CREATE TABLE IF NOT EXISTS `prints` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `email address` tinytext DEFAULT NULL,
  `project type` tinytext DEFAULT NULL,
  `gcode filename` tinytext DEFAULT NULL,
  `drive file id` tinytext DEFAULT NULL,
  `filament estimate` float unsigned DEFAULT NULL,
  `printer type` text DEFAULT NULL,
  `rep check` tinytext DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `print status` tinytext DEFAULT 'Pending Check',
  `assigned printer` int(11) DEFAULT NULL,
  `expected duration` time DEFAULT NULL,
  `added` datetime DEFAULT current_timestamp(),
  `last updated` datetime DEFAULT NULL ON UPDATE current_timestamp(),
  `start time` datetime DEFAULT NULL,
  `finish time` datetime DEFAULT NULL,
  `completion time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IF(@OLD_FOREIGN_KEY_CHECKS IS NULL, 1, @OLD_FOREIGN_KEY_CHECKS) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
