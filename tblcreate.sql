-- Hôte : localhost
-- Généré le :  ven. 29 mars 2019 à 14:50
-- Version du serveur :  5.5.57-MariaDB
-- Version de PHP :  5.6.38

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";

--
-- Base de données :  `FREEBOX`
--

-- --------------------------------------------------------

--
-- Structure de la table `calls`
--

CREATE TABLE `calls` (
  `id` int(11) NOT NULL COMMENT 'Primary key',
  `type` varchar(11) NOT NULL COMMENT 'missed,accepted,outgoing',
  `datetime` datetime NOT NULL COMMENT 'Call creation timestamp',
  `number` varchar(40) NOT NULL COMMENT 'Callee number for outgoing calls. Caller number for incoming calls.',
  `name` varchar(80) NOT NULL COMMENT 'Callee name for outgoing calls. Caller name for incoming calls.',
  `duration` int(11) NOT NULL COMMENT 'Call duration in seconds.',
  `new` tinyint(1) NOT NULL COMMENT 'Call entry as not been acknowledged yet.',
  `contact_id` int(11) NOT NULL COMMENT 'If the number matches an entry in the contact database, the id of the matching contact.',
  `src` varchar(40) NOT NULL DEFAULT '' COMMENT 'Source',
  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Last update timestamp'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Déclencheurs `calls`
--
DELIMITER $$
CREATE TRIGGER `update_calls_time` BEFORE UPDATE ON `calls` FOR EACH ROW BEGIN
  IF new.`id`=old.`id` THEN
   SET new.`UpdatedInDB`=CURRENT_TIMESTAMP();
  END IF;
END
$$
DELIMITER ;

--
-- Index pour les tables déchargées
--

--
-- Index pour la table `calls`
--
ALTER TABLE `calls`
  ADD PRIMARY KEY (`id`);
COMMIT;

-- --------------------------------------------------------

--
-- Structure de la table `fwredir`
--

CREATE TABLE `fwredir` (
  `id` int(11) NOT NULL COMMENT 'Primary key',
  `src_ip` varchar(15) NOT NULL COMMENT 'source ip',
  `ip_proto` varchar(10) NOT NULL COMMENT 'tcp,udp',
  `wan_port_start` int(11) NOT NULL COMMENT 'forwarding range start',
  `wan_port_end` int(11) NOT NULL COMMENT 'forwarding range end',
  `lan_port` int(11) NOT NULL COMMENT 'forwarding target on LAN',
  `lan_ip` varchar(15) NOT NULL COMMENT 'forwarding target start port on LAN',
  `hostname` varchar(40) NOT NULL COMMENT 'forwarding target host name',
  `enabled` varchar(5) NOT NULL COMMENT 'is forwarding enabled',
  `comment` varchar(80) NOT NULL COMMENT 'comment',
  `UpdatedInDb` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Last update timestamp'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Déclencheurs `fwredir`
--
DELIMITER $$
CREATE TRIGGER `update_fwredir_time` BEFORE UPDATE ON `fwredir` FOR EACH ROW BEGIN
  IF new.`id`=old.`id` THEN
   SET new.`UpdatedInDB`=CURRENT_TIMESTAMP();
  END IF;
END
$$
DELIMITER ;

--
-- Index pour les tables déchargées
--

--
-- Index pour la table `calls`
--
ALTER TABLE `calls`
  ADD PRIMARY KEY (`id`);

--
-- Index pour la table `fwredir`
--
ALTER TABLE `fwredir`
  ADD PRIMARY KEY (`id`);
COMMIT;

-- --------------------------------------------------------

--
-- Structure de la table `static_leases`
--

CREATE TABLE `static_leases` (
  `id` varchar(17) NOT NULL COMMENT 'Primary key',
  `mac` varchar(17) NOT NULL COMMENT 'Host mac address',
  `ip` varchar(27) NOT NULL COMMENT 'IPv4 to assign to the host',
  `is_static` tinyint(1) NOT NULL DEFAULT '1' COMMENT 'is the lease static',
  `assigned` datetime DEFAULT NULL COMMENT 'timestamp of the lease first assignment',
  `comment` varchar(40) NOT NULL COMMENT 'comment',
  `UpdatedInDb` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Last update timestamp'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Leases static Freebox';

--
-- Déclencheurs `static_leases`
--
DELIMITER $$
CREATE TRIGGER `update_lease_time` BEFORE UPDATE ON `static_leases` FOR EACH ROW BEGIN
  IF new.`id`=old.`id` THEN
   SET new.`UpdatedInDB`=CURRENT_TIMESTAMP();
  END IF;
END
$$
DELIMITER ;

--
-- Index pour les tables déchargées
--

--
-- Index pour la table `static_leases`
--
ALTER TABLE `static_leases`
  ADD PRIMARY KEY (`id`);
COMMIT;
