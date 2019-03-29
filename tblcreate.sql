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
