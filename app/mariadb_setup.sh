#!/bin/bash
#
# Original Author: Bert Van Vreckem <bert.vanvreckem@gmail.com>
# Modified By: Harry Merckel <harrymerckel@gmail.com>
#
# A non-interactive replacement for mysql_secure_installation
# With automated setup of print queue database

echo "[mysqld]" >> /etc/mysql/my.cnf
echo "skip-networking=0" >> /etc/mysql/my.cnf
echo "skip-bind-address" >> /etc/mysql/my.cnf

/etc/init.d/mysql start

set -o errexit # abort on nonzero exitstatus
set -o nounset # abort on unbound variable

#{{{ Functions

usage() {
cat << _EOF_

Usage: ${0} "ROOT PASSWORD" "SYS PASSWORD"

  with "ROOT PASSWORD" the desired password for the database root user and "SYS PASSWORD" is for the system to access data

Use quotes if your password contains spaces or other special characters.
_EOF_
}

# Predicate that returns exit status 0 if the database root password
# is set, a nonzero exit status otherwise.
is_mysql_root_password_set() {
  ! mysqladmin --user=root status > /dev/null 2>&1
}

# Predicate that returns exit status 0 if the mysql(1) command is available,
# nonzero exit status otherwise.
is_mysql_command_available() {
  which mysql > /dev/null 2>&1
}

#}}}
#{{{ Command line parsing

if [ "$#" -ne "2" ]; then
  echo "Expected 2 arguments, got $#" >&2
  usage
  exit 2
fi

#}}}
#{{{ Variables
db_root_password="${1}"
db_sys_password="${2}"
#}}}

# Script proper

if ! is_mysql_command_available; then
  echo "The MySQL/MariaDB client mysql(1) is not installed."
  exit 1
fi

if is_mysql_root_password_set; then
  echo "Database root password already set"
  exit 0
fi

mysql --user=root << _EOF_
  UPDATE mysql.user SET Password=PASSWORD('${db_root_password}') WHERE User='root';
  DELETE FROM mysql.user WHERE User='';
  DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
  DROP DATABASE IF EXISTS test;
  DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
  FLUSH PRIVILEGES;

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;

CREATE DATABASE IF NOT EXISTS \`queue\` /*!40100 DEFAULT CHARACTER SET latin1 */;
USE \`queue\`;

CREATE TABLE IF NOT EXISTS \`printers\` (
  \`id\` int(11) NOT NULL AUTO_INCREMENT,
  \`name\` tinytext DEFAULT NULL,
  \`type\` tinytext DEFAULT NULL,
  \`ip address\` tinytext DEFAULT NULL,
  \`api key\` tinytext DEFAULT NULL,
  \`total time printed\` int(10) unsigned DEFAULT 0,
  \`maintenance time\` int(10) unsigned DEFAULT 0,
  \`completed prints\` int(10) unsigned DEFAULT 0,
  \`failed prints\` int(10) unsigned DEFAULT 0,
  \`total filament used\` float unsigned DEFAULT 0,
  PRIMARY KEY (\`id\`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS \`prints\` (
  \`id\` int(11) NOT NULL AUTO_INCREMENT,
  \`email address\` tinytext DEFAULT NULL,
  \`project type\` tinytext DEFAULT NULL,
  \`gcode filename\` tinytext DEFAULT NULL,
  \`drive file id\` tinytext DEFAULT NULL,
  \`filament estimate\` float unsigned DEFAULT NULL,
  \`printer type\` text DEFAULT NULL,
  \`rep check\` tinytext DEFAULT NULL,
  \`notes\` text DEFAULT NULL,
  \`print status\` tinytext DEFAULT 'Pending Check',
  \`assigned printer\` int(11) DEFAULT NULL,
  \`expected duration\` time DEFAULT NULL,
  \`added\` datetime DEFAULT current_timestamp(),
  \`last updated\` datetime DEFAULT NULL ON UPDATE current_timestamp(),
  \`start time\` datetime DEFAULT NULL,
  \`finish time\` datetime DEFAULT NULL,
  PRIMARY KEY (\`id\`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=latin1;

/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IF(@OLD_FOREIGN_KEY_CHECKS IS NULL, 1, @OLD_FOREIGN_KEY_CHECKS) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;

  CREATE USER 'system' IDENTIFIED BY '${db_sys_password}';
  GRANT ALL privileges ON \`queue\`.* TO 'system'@'%';
  FLUSH PRIVILEGES;

_EOF_

if [ -f "/data/queue_backup.sql" ]; then
    mysql queue < /data/queue_backup.sql
fi