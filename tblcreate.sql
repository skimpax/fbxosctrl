-- phpMyAdmin SQL Dump
-- version 4.8.2
-- https://www.phpmyadmin.net/
--
-- Hôte : localhost
-- Généré le :  sam. 04 mai 2019 à 23:31
-- Version du serveur :  5.5.57-MariaDB
-- Version de PHP :  5.6.38

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";

--
-- Base de données :  `FREEBOX_NEW`
--

-- --------------------------------------------------------

--
-- Structure de la table `call_log`
--

CREATE TABLE `call_log` (
  `id` int(11) NOT NULL,
  `type` varchar(11) COLLATE utf8_bin NOT NULL COMMENT 'missed,accepted,outgoing',
  `datetime` datetime NOT NULL COMMENT 'call creation timestamp',
  `number` varchar(40) COLLATE utf8_bin NOT NULL COMMENT 'Callee number for outgoing calls. Caller number for incoming calls.',
  `name` varchar(80) COLLATE utf8_bin NOT NULL COMMENT 'Callee name for outgoing calls. Caller name for incoming calls.',
  `duration` int(11) NOT NULL COMMENT 'Call duration in seconds.',
  `new` tinyint(1) NOT NULL COMMENT 'Call entry as not been acknowledged yet.',
  `contact_id` int(11) NOT NULL COMMENT 'If the number matches an entry in the contact database, the id of the matching contact.',
  `src` varchar(40) COLLATE utf8_bin NOT NULL COMMENT 'Freebox source.',
  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

--
-- Déclencheurs `call_log`
--
DELIMITER $$
CREATE TRIGGER `UpdatedInDB` BEFORE UPDATE ON `call_log` FOR EACH ROW BEGIN
  IF new.`id`=old.`id` THEN
   SET new.`UpdatedInDB`=CURRENT_TIMESTAMP();
  END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Structure de la table `contact`
--

CREATE TABLE `contact` (
  `id` int(11) NOT NULL COMMENT 'contact id',
  `display_name` varchar(80) COLLATE utf8_bin NOT NULL COMMENT 'contact display name',
  `first_name` varchar(80) COLLATE utf8_bin NOT NULL COMMENT 'contact first name',
  `last_name` varchar(80) COLLATE utf8_bin NOT NULL COMMENT 'contact last name',
  `birthday` datetime NOT NULL COMMENT 'contact birthday',
  `company` varchar(80) COLLATE utf8_bin NOT NULL COMMENT 'contact company name',
  `photo_url` blob NOT NULL COMMENT 'contact photo URL, the photo URL can be embedded',
  `last_update` datetime NOT NULL COMMENT 'contact last modification timestamp',
  `notes` varchar(8192) COLLATE utf8_bin NOT NULL COMMENT 'notes',
  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

--
-- Déclencheurs `contact`
--
DELIMITER $$
CREATE TRIGGER `UpdatedInDB_contact` BEFORE UPDATE ON `contact` FOR EACH ROW BEGIN
  IF new.`id`=old.`id` THEN
   SET new.`UpdatedInDB`=CURRENT_TIMESTAMP();
  END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Structure de la table `contact_address`
--

CREATE TABLE `contact_address` (
  `id` int(11) NOT NULL,
  `contact_id` int(11) NOT NULL COMMENT 'contact id',
  `type` varchar(10) COLLATE utf8_bin NOT NULL COMMENT 'home, work, other',
  `number` varchar(128) COLLATE utf8_bin NOT NULL,
  `street` varchar(128) COLLATE utf8_bin NOT NULL,
  `street2` varchar(128) COLLATE utf8_bin NOT NULL,
  `city` varchar(80) COLLATE utf8_bin NOT NULL,
  `zipcode` varchar(80) COLLATE utf8_bin NOT NULL,
  `country` varchar(80) COLLATE utf8_bin NOT NULL,
  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

--
-- Déclencheurs `contact_address`
--
DELIMITER $$
CREATE TRIGGER `UpdatedInDB_address` BEFORE UPDATE ON `contact_address` FOR EACH ROW BEGIN
  IF new.`id`=old.`id` THEN
   SET new.`UpdatedInDB`=CURRENT_TIMESTAMP();
  END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Structure de la table `contact_email`
--

CREATE TABLE `contact_email` (
  `id` int(11) NOT NULL,
  `contact_id` int(11) NOT NULL COMMENT 'contact id',
  `type` varchar(10) COLLATE utf8_bin NOT NULL COMMENT 'home, work, other',
  `email` varchar(128) COLLATE utf8_bin NOT NULL,
  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

--
-- Déclencheurs `contact_email`
--
DELIMITER $$
CREATE TRIGGER `UpdatedInDB_email` BEFORE UPDATE ON `contact_email` FOR EACH ROW BEGIN
  IF new.`id`=old.`id` THEN
   SET new.`UpdatedInDB`=CURRENT_TIMESTAMP();
  END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Structure de la table `contact_group`
--

CREATE TABLE `contact_group` (
  `contact_id` int(11) NOT NULL COMMENT 'contact id',
  `group_id` int(11) NOT NULL COMMENT 'group id',
  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

--
-- Déclencheurs `contact_group`
--
DELIMITER $$
CREATE TRIGGER `UpdatedInDB_cgroup` BEFORE UPDATE ON `contact_group` FOR EACH ROW BEGIN
  IF new.`group_id`=old.`group_id` AND new.`contact_id`=old.`contact_id` THEN
   SET new.`UpdatedInDB`=CURRENT_TIMESTAMP();
  END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Structure de la table `contact_number`
--

CREATE TABLE `contact_number` (
  `id` int(11) NOT NULL,
  `contact_id` int(11) NOT NULL COMMENT 'contact id',
  `type` varchar(10) COLLATE utf8_bin NOT NULL COMMENT 'fixed, mobile, work, fax, other',
  `number` varchar(80) COLLATE utf8_bin NOT NULL,
  `is_default` tinyint(1) NOT NULL COMMENT 'is this number the preferred contact phone number',
  `is_own` tinyint(1) NOT NULL COMMENT 'is this number the Freebox owner number',
  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

--
-- Déclencheurs `contact_number`
--
DELIMITER $$
CREATE TRIGGER `UpdatedInDB_number` BEFORE UPDATE ON `contact_number` FOR EACH ROW BEGIN
  IF new.`id`=old.`id` THEN
   SET new.`UpdatedInDB`=CURRENT_TIMESTAMP();
  END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Structure de la table `contact_url`
--

CREATE TABLE `contact_url` (
  `id` int(11) NOT NULL,
  `contact_id` int(11) NOT NULL COMMENT 'contact id',
  `type` varchar(10) COLLATE utf8_bin NOT NULL COMMENT 'profile, blog, site, other',
  `url` varchar(128) COLLATE utf8_bin NOT NULL,
  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

--
-- Déclencheurs `contact_url`
--
DELIMITER $$
CREATE TRIGGER `UpdatedInDB_url` BEFORE UPDATE ON `contact_url` FOR EACH ROW BEGIN
  IF new.`id`=old.`id` THEN
   SET new.`UpdatedInDB`=CURRENT_TIMESTAMP();
  END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Structure de la table `dynamic_lease`
--

CREATE TABLE `dynamic_lease` (
  `mac` varchar(17) COLLATE utf8_bin NOT NULL COMMENT 'Host mac address',
  `hostname` varchar(40) COLLATE utf8_bin NOT NULL COMMENT 'hostname matching the mac address',
  `ip` varchar(27) COLLATE utf8_bin NOT NULL COMMENT 'IPv4 assigned to the host',
  `lease_remaining` int(11) NOT NULL COMMENT 'time left before lease needs to be refreshed',
  `assign_time` datetime NOT NULL COMMENT 'timestamp of the lease first assignment',
  `refresh_time` datetime NOT NULL COMMENT 'timestamp of the last lease refresh',
  `is_static` tinyint(1) NOT NULL COMMENT 'is the lease static',
  `comment` varchar(40) COLLATE utf8_bin NOT NULL COMMENT 'comment',
  `src` varchar(40) COLLATE utf8_bin NOT NULL COMMENT 'Freebox source.',
  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

--
-- Déclencheurs `dynamic_lease`
--
DELIMITER $$
CREATE TRIGGER `UpdatedInDB_dynlease` BEFORE UPDATE ON `dynamic_lease` FOR EACH ROW BEGIN
  IF new.`mac`=old.`mac` THEN
   SET new.`UpdatedInDB`=CURRENT_TIMESTAMP();
  END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Structure de la table `fw_redir`
--

CREATE TABLE `fw_redir` (
  `id` int(11) NOT NULL,
  `src_ip` varchar(15) COLLATE utf8_bin NOT NULL COMMENT 'source ip',
  `ip_proto` varchar(10) COLLATE utf8_bin NOT NULL COMMENT 'tcp,udp',
  `wan_port_start` int(11) NOT NULL COMMENT 'forwarding range start',
  `wan_port_end` int(11) NOT NULL COMMENT 'forwarding range end',
  `lan_port` int(11) NOT NULL COMMENT 'forwarding target on LAN',
  `lan_ip` varchar(15) COLLATE utf8_bin NOT NULL COMMENT 'forwarding target start port on LAN',
  `hostname` varchar(40) COLLATE utf8_bin NOT NULL COMMENT 'forwarding target host name',
  `enabled` tinyint(1) NOT NULL COMMENT 'is forwarding enabled',
  `comment` varchar(80) COLLATE utf8_bin NOT NULL COMMENT 'comment',
  `src` varchar(40) COLLATE utf8_bin NOT NULL COMMENT 'Freebox source.',
  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

--
-- Déclencheurs `fw_redir`
--
DELIMITER $$
CREATE TRIGGER `UpdatedInDB_fwredir` BEFORE UPDATE ON `fw_redir` FOR EACH ROW BEGIN
  IF new.`id`=old.`id` THEN
   SET new.`UpdatedInDB`=CURRENT_TIMESTAMP();
  END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Structure de la table `group`
--

CREATE TABLE `group` (
  `id` int(11) NOT NULL COMMENT 'group id',
  `name` varchar(80) COLLATE utf8_bin NOT NULL COMMENT 'group name',
  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

--
-- Déclencheurs `group`
--
DELIMITER $$
CREATE TRIGGER `UpdatedInDB_group` BEFORE UPDATE ON `group` FOR EACH ROW BEGIN
  IF new.`id`=old.`id` THEN
   SET new.`UpdatedInDB`=CURRENT_TIMESTAMP();
  END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Structure de la table `static_lease`
--

CREATE TABLE `static_lease` (
  `id` varchar(17) COLLATE utf8_bin NOT NULL COMMENT 'Primary key',
  `mac` varchar(17) COLLATE utf8_bin NOT NULL COMMENT 'Host mac address',
  `comment` varchar(40) COLLATE utf8_bin NOT NULL COMMENT 'comment',
  `hostname` varchar(40) COLLATE utf8_bin NOT NULL COMMENT 'hostname matching the mac address',
  `ip` varchar(27) COLLATE utf8_bin NOT NULL COMMENT 'IPv4 to assign to the host',
  `reachable` tinyint(1) NOT NULL COMMENT 'If true the host can receive traffic from the Freebox',
  `last_activity` datetime NOT NULL COMMENT 'Last time the host sent traffic',
  `last_time_reachable` datetime NOT NULL COMMENT 'Last time the host was reached',
  `src` varchar(40) COLLATE utf8_bin NOT NULL COMMENT 'Freebox source.',
  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

--
-- Déclencheurs `static_lease`
--
DELIMITER $$
CREATE TRIGGER `UpdatedInDB_stlease` BEFORE UPDATE ON `static_lease` FOR EACH ROW BEGIN
  IF new.`id`=old.`id` THEN
   SET new.`UpdatedInDB`=CURRENT_TIMESTAMP();
  END IF;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Doublure de structure pour la vue `vaddresses`
-- (Voir ci-dessous la vue réelle)
--
CREATE TABLE `vaddresses` (
`id` int(11)
,`contact_id` int(11)
,`type` varchar(10)
,`number` varchar(128)
,`street` varchar(128)
,`street2` varchar(128)
,`zipcode` varchar(80)
,`city` varchar(80)
,`country` varchar(80)
,`display_name` varchar(80)
,`last_name` varchar(80)
,`first_name` varchar(80)
,`company` varchar(80)
);

-- --------------------------------------------------------

--
-- Doublure de structure pour la vue `vcontacts`
-- (Voir ci-dessous la vue réelle)
--
CREATE TABLE `vcontacts` (
`id` int(11)
,`display_name` varchar(80)
,`company` varchar(80)
,`type` varchar(10)
,`number` varchar(80)
,`notes` varchar(8192)
);

-- --------------------------------------------------------

--
-- Doublure de structure pour la vue `vemails`
-- (Voir ci-dessous la vue réelle)
--
CREATE TABLE `vemails` (
`id` int(11)
,`contact_id` int(11)
,`type` varchar(10)
,`email` varchar(128)
,`display_name` varchar(80)
,`last_name` varchar(80)
,`first_name` varchar(80)
,`company` varchar(80)
,`notes` varchar(8192)
);

-- --------------------------------------------------------

--
-- Doublure de structure pour la vue `vleases`
-- (Voir ci-dessous la vue réelle)
--
CREATE TABLE `vleases` (
`id` varchar(17)
,`mac` varchar(17)
,`ip` varchar(27)
,`is_static` tinyint(1)
,`assigned` datetime
,`comment` varchar(40)
,`ip4` bigint(21) unsigned
);

-- --------------------------------------------------------

--
-- Doublure de structure pour la vue `vnumbers`
-- (Voir ci-dessous la vue réelle)
--
CREATE TABLE `vnumbers` (
`id` int(11)
,`contact_id` int(11)
,`type` varchar(10)
,`number` varchar(80)
,`is_default` tinyint(1)
,`is_own` tinyint(1)
,`display_name` varchar(80)
,`last_name` varchar(80)
,`first_name` varchar(80)
,`company` varchar(80)
,`notes` varchar(8192)
);

-- --------------------------------------------------------

--
-- Doublure de structure pour la vue `vurls`
-- (Voir ci-dessous la vue réelle)
--
CREATE TABLE `vurls` (
`id` int(11)
,`contact_id` int(11)
,`type` varchar(10)
,`url` varchar(128)
,`display_name` varchar(80)
,`last_name` varchar(80)
,`first_name` varchar(80)
,`company` varchar(80)
);

-- --------------------------------------------------------

--
-- Structure de la vue `vaddresses`
--
DROP TABLE IF EXISTS `vaddresses`;

CREATE ALGORITHM=UNDEFINED DEFINER=`admin`@`localhost` SQL SECURITY DEFINER VIEW `vaddresses`  AS  select `contact_address`.`id` AS `id`,`contact_address`.`contact_id` AS `contact_id`,`contact_address`.`type` AS `type`,`contact_address`.`number` AS `number`,`contact_address`.`street` AS `street`,`contact_address`.`street2` AS `street2`,`contact_address`.`zipcode` AS `zipcode`,`contact_address`.`city` AS `city`,`contact_address`.`country` AS `country`,`contact`.`display_name` AS `display_name`,`contact`.`last_name` AS `last_name`,`contact`.`first_name` AS `first_name`,`contact`.`company` AS `company` from (`contact_address` left join `contact` on((`contact_address`.`contact_id` = `contact`.`id`))) ;

-- --------------------------------------------------------

--
-- Structure de la vue `vcontacts`
--
DROP TABLE IF EXISTS `vcontacts`;

CREATE ALGORITHM=UNDEFINED DEFINER=`admin`@`localhost` SQL SECURITY DEFINER VIEW `vcontacts`  AS  select `contact`.`id` AS `id`,`contact`.`display_name` AS `display_name`,`contact`.`company` AS `company`,`contact_number`.`type` AS `type`,`contact_number`.`number` AS `number`,`contact`.`notes` AS `notes` from (`contact` join `contact_number`) where (`contact`.`id` = `contact_number`.`contact_id`) ;

-- --------------------------------------------------------

--
-- Structure de la vue `vemails`
--
DROP TABLE IF EXISTS `vemails`;

CREATE ALGORITHM=UNDEFINED DEFINER=`admin`@`localhost` SQL SECURITY DEFINER VIEW `vemails`  AS  select `contact_email`.`id` AS `id`,`contact_email`.`contact_id` AS `contact_id`,`contact_email`.`type` AS `type`,`contact_email`.`email` AS `email`,`contact`.`display_name` AS `display_name`,`contact`.`last_name` AS `last_name`,`contact`.`first_name` AS `first_name`,`contact`.`company` AS `company`,`contact`.`notes` AS `notes` from (`contact_email` left join `contact` on((`contact_email`.`contact_id` = `contact`.`id`))) ;

-- --------------------------------------------------------

--
-- Structure de la vue `vleases`
--
DROP TABLE IF EXISTS `vleases`;

CREATE ALGORITHM=UNDEFINED DEFINER=`admin`@`localhost` SQL SECURITY DEFINER VIEW `vleases`  AS  select `dynamic_lease`.`mac` AS `id`,`dynamic_lease`.`mac` AS `mac`,`dynamic_lease`.`ip` AS `ip`,`dynamic_lease`.`is_static` AS `is_static`,`dynamic_lease`.`assign_time` AS `assigned`,`dynamic_lease`.`comment` AS `comment`,cast(substr(`dynamic_lease`.`ip`,(length(substring_index(`dynamic_lease`.`ip`,'.',3)) + 2)) as unsigned) AS `ip4` from `dynamic_lease` order by cast(substr(`dynamic_lease`.`ip`,(length(substring_index(`dynamic_lease`.`ip`,'.',3)) + 2)) as unsigned) ;

-- --------------------------------------------------------

--
-- Structure de la vue `vnumbers`
--
DROP TABLE IF EXISTS `vnumbers`;

CREATE ALGORITHM=UNDEFINED DEFINER=`admin`@`localhost` SQL SECURITY DEFINER VIEW `vnumbers`  AS  select `contact_number`.`id` AS `id`,`contact_number`.`contact_id` AS `contact_id`,`contact_number`.`type` AS `type`,`contact_number`.`number` AS `number`,`contact_number`.`is_default` AS `is_default`,`contact_number`.`is_own` AS `is_own`,`contact`.`display_name` AS `display_name`,`contact`.`last_name` AS `last_name`,`contact`.`first_name` AS `first_name`,`contact`.`company` AS `company`,`contact`.`notes` AS `notes` from (`contact_number` left join `contact` on((`contact_number`.`contact_id` = `contact`.`id`))) ;

-- --------------------------------------------------------

--
-- Structure de la vue `vurls`
--
DROP TABLE IF EXISTS `vurls`;

CREATE ALGORITHM=UNDEFINED DEFINER=`admin`@`localhost` SQL SECURITY DEFINER VIEW `vurls`  AS  select `contact_url`.`id` AS `id`,`contact_url`.`contact_id` AS `contact_id`,`contact_url`.`type` AS `type`,`contact_url`.`url` AS `url`,`contact`.`display_name` AS `display_name`,`contact`.`last_name` AS `last_name`,`contact`.`first_name` AS `first_name`,`contact`.`company` AS `company` from (`contact_url` left join `contact` on((`contact_url`.`contact_id` = `contact`.`id`))) ;

--
-- Index pour les tables déchargées
--

--
-- Index pour la table `call_log`
--
ALTER TABLE `call_log`
  ADD PRIMARY KEY (`id`,`src`) USING BTREE;

--
-- Index pour la table `contact`
--
ALTER TABLE `contact`
  ADD PRIMARY KEY (`id`);

--
-- Index pour la table `contact_address`
--
ALTER TABLE `contact_address`
  ADD PRIMARY KEY (`id`);

--
-- Index pour la table `contact_email`
--
ALTER TABLE `contact_email`
  ADD PRIMARY KEY (`id`);

--
-- Index pour la table `contact_group`
--
ALTER TABLE `contact_group`
  ADD PRIMARY KEY (`group_id`,`contact_id`);

--
-- Index pour la table `contact_number`
--
ALTER TABLE `contact_number`
  ADD PRIMARY KEY (`id`);

--
-- Index pour la table `contact_url`
--
ALTER TABLE `contact_url`
  ADD PRIMARY KEY (`id`);

--
-- Index pour la table `dynamic_lease`
--
ALTER TABLE `dynamic_lease`
  ADD PRIMARY KEY (`mac`);

--
-- Index pour la table `fw_redir`
--
ALTER TABLE `fw_redir`
  ADD PRIMARY KEY (`id`);

--
-- Index pour la table `group`
--
ALTER TABLE `group`
  ADD PRIMARY KEY (`id`);

--
-- Index pour la table `static_lease`
--
ALTER TABLE `static_lease`
  ADD PRIMARY KEY (`id`);
COMMIT;
