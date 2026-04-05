-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: banco_painel_banco:3306
-- Tempo de geração: 03/04/2026 às 02:00
-- Versão do servidor: 9.6.0
-- Versão do PHP: 8.2.27

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `dados`
--

-- --------------------------------------------------------

--
-- Estrutura para tabela `atividades`
--

CREATE TABLE `atividades` (
  `id_atividade` int NOT NULL,
  `titulo` varchar(160) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao` text COLLATE utf8mb4_unicode_ci,
  `dificuldade` enum('facil','media','dificil','critica') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'media',
  `estimativa_horas` decimal(6,2) NOT NULL DEFAULT '0.00',
  `status` enum('aberta','em_andamento','concluida','cancelada') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'aberta',
  `criado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `atividades`
--

INSERT INTO `atividades` (`id_atividade`, `titulo`, `descricao`, `dificuldade`, `estimativa_horas`, `status`, `criado_em`, `atualizado_em`) VALUES
(3, 'canal tal editar', 'tal tal tal', 'dificil', 2.00, 'aberta', '2026-02-04 00:05:02', '2026-02-04 00:47:16'),
(4, 'Editor de video', NULL, 'media', 8.00, 'aberta', '2026-02-11 01:17:19', '2026-02-11 01:17:19');

-- --------------------------------------------------------

--
-- Estrutura para tabela `atividades_subtarefas`
--

CREATE TABLE `atividades_subtarefas` (
  `id_subtarefa` bigint NOT NULL,
  `id_atividade` int NOT NULL,
  `user_id` varchar(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `referencia_data` date DEFAULT NULL,
  `titulo` varchar(220) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `canal_entrega` varchar(180) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `concluida` tinyint(1) NOT NULL DEFAULT '0',
  `segundos_gastos` int NOT NULL DEFAULT '0',
  `observacao` varchar(600) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_sessao` bigint DEFAULT NULL,
  `id_relatorio` int DEFAULT NULL,
  `criada_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `concluida_em` datetime DEFAULT NULL,
  `atualizada_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `bloqueada_pagamento` tinyint(1) NOT NULL DEFAULT '0',
  `id_pagamento` int DEFAULT NULL,
  `bloqueada_em` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `atividades_subtarefas`
--

INSERT INTO `atividades_subtarefas` (`id_subtarefa`, `id_atividade`, `user_id`, `referencia_data`, `titulo`, `canal_entrega`, `concluida`, `segundos_gastos`, `observacao`, `id_sessao`, `id_relatorio`, `criada_em`, `concluida_em`, `atualizada_em`, `bloqueada_pagamento`, `id_pagamento`, `bloqueada_em`) VALUES
(3, 3, 'lucas', NULL, 'fazer tumbnail canal tal1', NULL, 1, 0, NULL, NULL, NULL, '2026-02-04 14:20:50', '2026-02-04 14:22:47', '2026-02-04 14:22:47', 0, NULL, NULL),
(4, 3, 'lucas', NULL, 'editar video tal do canal tal2', NULL, 1, 0, NULL, NULL, NULL, '2026-02-04 14:21:09', '2026-02-04 14:22:43', '2026-02-04 14:22:43', 0, NULL, NULL),
(7, 3, 'lucas', '2026-03-25', 'adwadadwwww', 'ddddddd', 1, 38, 'aaaaaaa', NULL, NULL, '2026-03-25 23:31:14', '2026-03-25 23:31:31', '2026-03-25 23:31:31', 0, NULL, NULL),
(8, 4, 'rafael', '2026-03-26', 'Video 1', 'Brian Cox', 1, 180, NULL, NULL, NULL, '2026-03-26 17:09:00', '2026-03-26 17:09:52', '2026-03-26 17:16:15', 0, NULL, NULL),
(10, 4, 'rafael', '2026-03-26', 'Teste', 'asdasd', 1, 360, 'asdasd', NULL, NULL, '2026-03-26 17:16:37', '2026-03-26 17:17:03', '2026-03-26 17:17:29', 0, NULL, NULL),
(11, 3, 'lucas', '2026-04-02', 'dadwad', 'dadadw', 1, 14, 'dwadwad', NULL, NULL, '2026-04-03 01:40:34', '2026-04-03 01:41:50', '2026-04-03 01:41:50', 0, NULL, NULL);

-- --------------------------------------------------------

--
-- Estrutura para tabela `atividades_subtarefas_historico`
--

CREATE TABLE `atividades_subtarefas_historico` (
  `id_historico` bigint NOT NULL,
  `id_subtarefa` bigint NOT NULL,
  `acao` enum('criacao','edicao','exclusao','conclusao','reabertura','bloqueio_pagamento') COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id_alvo` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id_executor` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dados_antes` json DEFAULT NULL,
  `dados_depois` json DEFAULT NULL,
  `criado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `atividades_subtarefas_historico`
--

INSERT INTO `atividades_subtarefas_historico` (`id_historico`, `id_subtarefa`, `acao`, `user_id_alvo`, `user_id_executor`, `dados_antes`, `dados_depois`, `criado_em`) VALUES
(7, 7, 'criacao', 'lucas', 'lucas', NULL, '{\"titulo\": \"adwadadwwww\", \"observacao\": \"aaaaaaa\", \"id_atividade\": 3, \"canal_entrega\": \"ddddddd\", \"referencia_data\": \"2026-03-25\"}', '2026-03-25 23:31:14'),
(8, 7, 'conclusao', 'lucas', 'lucas', '{\"titulo\": \"adwadadwwww\", \"user_id\": \"lucas\", \"concluida\": 0, \"criada_em\": \"2026-03-25 23:31:14\", \"id_sessao\": null, \"observacao\": \"aaaaaaa\", \"bloqueada_em\": null, \"concluida_em\": null, \"id_atividade\": 3, \"id_pagamento\": null, \"id_relatorio\": null, \"id_subtarefa\": 7, \"atualizada_em\": \"2026-03-25 23:31:14\", \"canal_entrega\": \"ddddddd\", \"referencia_data\": \"2026-03-25\", \"segundos_gastos\": 0, \"titulo_atividade\": \"canal tal editar\", \"bloqueada_pagamento\": 0}', '{\"titulo\": \"adwadadwwww\", \"user_id\": \"lucas\", \"concluida\": 1, \"criada_em\": \"2026-03-25 23:31:14\", \"id_sessao\": null, \"observacao\": \"aaaaaaa\", \"bloqueada_em\": null, \"concluida_em\": \"2026-03-25 23:31:31\", \"id_atividade\": 3, \"id_pagamento\": null, \"id_relatorio\": null, \"id_subtarefa\": 7, \"atualizada_em\": \"2026-03-25 23:31:31\", \"canal_entrega\": \"ddddddd\", \"referencia_data\": \"2026-03-25\", \"segundos_gastos\": 38, \"titulo_atividade\": \"canal tal editar\", \"bloqueada_pagamento\": 0}', '2026-03-25 23:31:32'),
(9, 8, 'criacao', 'rafael', 'rafael', NULL, '{\"titulo\": \"Video 1\", \"observacao\": null, \"id_atividade\": 4, \"canal_entrega\": \"Brian Cox\", \"referencia_data\": \"2026-03-26\"}', '2026-03-26 17:09:00'),
(10, 8, 'conclusao', 'rafael', 'rafael', '{\"titulo\": \"Video 1\", \"user_id\": \"rafael\", \"concluida\": 0, \"criada_em\": \"2026-03-26 17:09:00\", \"id_sessao\": null, \"observacao\": \"\", \"bloqueada_em\": null, \"concluida_em\": null, \"id_atividade\": 4, \"id_pagamento\": null, \"id_relatorio\": null, \"id_subtarefa\": 8, \"atualizada_em\": \"2026-03-26 17:09:00\", \"canal_entrega\": \"Brian Cox\", \"referencia_data\": \"2026-03-26\", \"segundos_gastos\": 0, \"titulo_atividade\": \"Editor de video\", \"bloqueada_pagamento\": 0}', '{\"titulo\": \"Video 1\", \"user_id\": \"rafael\", \"concluida\": 1, \"criada_em\": \"2026-03-26 17:09:00\", \"id_sessao\": null, \"observacao\": \"\", \"bloqueada_em\": null, \"concluida_em\": \"2026-03-26 17:09:52\", \"id_atividade\": 4, \"id_pagamento\": null, \"id_relatorio\": null, \"id_subtarefa\": 8, \"atualizada_em\": \"2026-03-26 17:09:52\", \"canal_entrega\": \"Brian Cox\", \"referencia_data\": \"2026-03-26\", \"segundos_gastos\": 300, \"titulo_atividade\": \"Editor de video\", \"bloqueada_pagamento\": 0}', '2026-03-26 17:09:53'),
(13, 8, 'edicao', 'rafael', 'rafael', '{\"titulo\": \"Video 1\", \"user_id\": \"rafael\", \"concluida\": 1, \"criada_em\": \"2026-03-26 17:09:00\", \"id_sessao\": null, \"observacao\": \"\", \"bloqueada_em\": null, \"concluida_em\": \"2026-03-26 17:09:52\", \"id_atividade\": 4, \"id_pagamento\": null, \"id_relatorio\": null, \"id_subtarefa\": 8, \"atualizada_em\": \"2026-03-26 17:09:52\", \"canal_entrega\": \"Brian Cox\", \"referencia_data\": \"2026-03-26\", \"segundos_gastos\": 300, \"titulo_atividade\": \"Editor de video\", \"bloqueada_pagamento\": 0}', '{\"titulo\": \"Video 1\", \"user_id\": \"rafael\", \"concluida\": 1, \"criada_em\": \"2026-03-26 17:09:00\", \"id_sessao\": null, \"observacao\": \"\", \"bloqueada_em\": null, \"concluida_em\": \"2026-03-26 17:09:52\", \"id_atividade\": 4, \"id_pagamento\": null, \"id_relatorio\": null, \"id_subtarefa\": 8, \"atualizada_em\": \"2026-03-26 17:16:15\", \"canal_entrega\": \"Brian Cox\", \"referencia_data\": \"2026-03-26\", \"segundos_gastos\": 180, \"titulo_atividade\": \"Editor de video\", \"bloqueada_pagamento\": 0}', '2026-03-26 17:16:16'),
(14, 10, 'criacao', 'rafael', 'rafael', NULL, '{\"titulo\": \"Teste\", \"observacao\": \"asdasd\", \"id_atividade\": 4, \"canal_entrega\": \"asdasd\", \"referencia_data\": \"2026-03-26\"}', '2026-03-26 17:16:37'),
(15, 10, 'conclusao', 'rafael', 'rafael', '{\"titulo\": \"Teste\", \"user_id\": \"rafael\", \"concluida\": 0, \"criada_em\": \"2026-03-26 17:16:37\", \"id_sessao\": null, \"observacao\": \"asdasd\", \"bloqueada_em\": null, \"concluida_em\": null, \"id_atividade\": 4, \"id_pagamento\": null, \"id_relatorio\": null, \"id_subtarefa\": 10, \"atualizada_em\": \"2026-03-26 17:16:37\", \"canal_entrega\": \"asdasd\", \"referencia_data\": \"2026-03-26\", \"segundos_gastos\": 0, \"titulo_atividade\": \"Editor de video\", \"bloqueada_pagamento\": 0}', '{\"titulo\": \"Teste\", \"user_id\": \"rafael\", \"concluida\": 1, \"criada_em\": \"2026-03-26 17:16:37\", \"id_sessao\": null, \"observacao\": \"asdasd\", \"bloqueada_em\": null, \"concluida_em\": \"2026-03-26 17:17:03\", \"id_atividade\": 4, \"id_pagamento\": null, \"id_relatorio\": null, \"id_subtarefa\": 10, \"atualizada_em\": \"2026-03-26 17:17:03\", \"canal_entrega\": \"asdasd\", \"referencia_data\": \"2026-03-26\", \"segundos_gastos\": 300, \"titulo_atividade\": \"Editor de video\", \"bloqueada_pagamento\": 0}', '2026-03-26 17:17:04'),
(16, 10, 'edicao', 'rafael', 'rafael', '{\"titulo\": \"Teste\", \"user_id\": \"rafael\", \"concluida\": 1, \"criada_em\": \"2026-03-26 17:16:37\", \"id_sessao\": null, \"observacao\": \"asdasd\", \"bloqueada_em\": null, \"concluida_em\": \"2026-03-26 17:17:03\", \"id_atividade\": 4, \"id_pagamento\": null, \"id_relatorio\": null, \"id_subtarefa\": 10, \"atualizada_em\": \"2026-03-26 17:17:03\", \"canal_entrega\": \"asdasd\", \"referencia_data\": \"2026-03-26\", \"segundos_gastos\": 300, \"titulo_atividade\": \"Editor de video\", \"bloqueada_pagamento\": 0}', '{\"titulo\": \"Teste\", \"user_id\": \"rafael\", \"concluida\": 1, \"criada_em\": \"2026-03-26 17:16:37\", \"id_sessao\": null, \"observacao\": \"asdasd\", \"bloqueada_em\": null, \"concluida_em\": \"2026-03-26 17:17:03\", \"id_atividade\": 4, \"id_pagamento\": null, \"id_relatorio\": null, \"id_subtarefa\": 10, \"atualizada_em\": \"2026-03-26 17:17:29\", \"canal_entrega\": \"asdasd\", \"referencia_data\": \"2026-03-26\", \"segundos_gastos\": 360, \"titulo_atividade\": \"Editor de video\", \"bloqueada_pagamento\": 0}', '2026-03-26 17:17:29'),
(17, 11, 'criacao', 'lucas', 'lucas', NULL, '{\"titulo\": \"dadwad\", \"observacao\": \"dwadwad\", \"id_atividade\": 3, \"canal_entrega\": \"dadadw\", \"referencia_data\": \"2026-04-02\"}', '2026-04-03 01:40:34'),
(18, 11, 'edicao', 'lucas', 'lucas', '{\"titulo\": \"dadwad\", \"user_id\": \"lucas\", \"concluida\": 0, \"criada_em\": \"2026-04-03 01:40:34\", \"id_sessao\": null, \"observacao\": \"dwadwad\", \"bloqueada_em\": null, \"concluida_em\": null, \"id_atividade\": 3, \"id_pagamento\": null, \"id_relatorio\": null, \"id_subtarefa\": 11, \"atualizada_em\": \"2026-04-03 01:40:34\", \"canal_entrega\": \"dadadw\", \"referencia_data\": \"2026-04-02\", \"segundos_gastos\": 0, \"titulo_atividade\": \"canal tal editar\", \"bloqueada_pagamento\": 0}', '{\"titulo\": \"dadwad\", \"user_id\": \"lucas\", \"concluida\": 0, \"criada_em\": \"2026-04-03 01:40:34\", \"id_sessao\": null, \"observacao\": \"dwadwad\", \"bloqueada_em\": null, \"concluida_em\": null, \"id_atividade\": 3, \"id_pagamento\": null, \"id_relatorio\": null, \"id_subtarefa\": 11, \"atualizada_em\": \"2026-04-03 01:40:34\", \"canal_entrega\": \"dadadw\", \"referencia_data\": \"2026-04-02\", \"segundos_gastos\": 0, \"titulo_atividade\": \"canal tal editar\", \"bloqueada_pagamento\": 0}', '2026-04-03 01:41:47'),
(19, 11, 'conclusao', 'lucas', 'lucas', '{\"titulo\": \"dadwad\", \"user_id\": \"lucas\", \"concluida\": 0, \"criada_em\": \"2026-04-03 01:40:34\", \"id_sessao\": null, \"observacao\": \"dwadwad\", \"bloqueada_em\": null, \"concluida_em\": null, \"id_atividade\": 3, \"id_pagamento\": null, \"id_relatorio\": null, \"id_subtarefa\": 11, \"atualizada_em\": \"2026-04-03 01:40:34\", \"canal_entrega\": \"dadadw\", \"referencia_data\": \"2026-04-02\", \"segundos_gastos\": 0, \"titulo_atividade\": \"canal tal editar\", \"bloqueada_pagamento\": 0}', '{\"titulo\": \"dadwad\", \"user_id\": \"lucas\", \"concluida\": 1, \"criada_em\": \"2026-04-03 01:40:34\", \"id_sessao\": null, \"observacao\": \"dwadwad\", \"bloqueada_em\": null, \"concluida_em\": \"2026-04-03 01:41:50\", \"id_atividade\": 3, \"id_pagamento\": null, \"id_relatorio\": null, \"id_subtarefa\": 11, \"atualizada_em\": \"2026-04-03 01:41:50\", \"canal_entrega\": \"dadadw\", \"referencia_data\": \"2026-04-02\", \"segundos_gastos\": 14, \"titulo_atividade\": \"canal tal editar\", \"bloqueada_pagamento\": 0}', '2026-04-03 01:41:50');

-- --------------------------------------------------------

--
-- Estrutura para tabela `atividades_usuarios`
--

CREATE TABLE `atividades_usuarios` (
  `id_vinculo` int NOT NULL,
  `id_atividade` int NOT NULL,
  `id_usuario` int NOT NULL,
  `atribuida_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `atividades_usuarios`
--

INSERT INTO `atividades_usuarios` (`id_vinculo`, `id_atividade`, `id_usuario`, `atribuida_em`) VALUES
(5, 3, 1, '2026-02-04 00:47:17'),
(7, 4, 2, '2026-03-26 17:02:30'),
(8, 4, 3, '2026-03-26 17:02:30');

-- --------------------------------------------------------

--
-- Estrutura para tabela `cronometro_apps_intervalos`
--

CREATE TABLE `cronometro_apps_intervalos` (
  `id_intervalo` bigint NOT NULL,
  `id_sessao` bigint NOT NULL,
  `user_id` varchar(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `nome_app` varchar(180) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `inicio_em` datetime NOT NULL,
  `fim_em` datetime DEFAULT NULL,
  `segundos_em_foco` int NOT NULL DEFAULT '0',
  `segundos_segundo_plano` int NOT NULL DEFAULT '0',
  `ultima_atualizacao_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `cronometro_apps_intervalos`
--

INSERT INTO `cronometro_apps_intervalos` (`id_intervalo`, `id_sessao`, `user_id`, `nome_app`, `inicio_em`, `fim_em`, `segundos_em_foco`, `segundos_segundo_plano`, `ultima_atualizacao_em`) VALUES
(181, 23, 'lucas', 'python3.12.exe', '2026-02-09 15:09:08', '2026-02-09 15:09:42', 8, 23, '2026-02-09 18:09:42'),
(182, 23, 'lucas', 'ms-teams.exe', '2026-02-09 15:09:18', '2026-02-09 15:10:03', 20, 23, '2026-02-09 18:10:02'),
(183, 23, 'lucas', 'chrome.exe', '2026-02-09 15:09:39', '2026-02-09 15:10:11', 20, 13, '2026-02-09 18:10:11'),
(184, 23, 'lucas', 'python3.12.exe', '2026-02-09 15:09:59', '2026-02-09 15:10:11', 4, 8, '2026-02-09 18:10:11'),
(185, 24, 'joao', 'cronometro.exe', '2026-02-10 22:29:43', '2026-02-10 22:32:50', 43, 142, '2026-02-11 01:32:05'),
(186, 25, 'joao', 'cronometro.exe', '2026-02-10 22:33:45', '2026-02-10 22:34:24', 14, 23, '2026-02-11 01:33:39'),
(187, 25, 'joao', 'chrome.exe', '2026-02-10 22:33:56', '2026-02-10 22:34:24', 23, 5, '2026-02-11 01:33:40'),
(188, 26, 'joao', 'cronometro.exe', '2026-02-10 22:42:42', '2026-02-10 22:42:53', 9, 0, '2026-02-11 01:42:08'),
(189, 27, 'joao', 'cronometro.exe', '2026-02-10 22:45:17', '2026-02-10 22:45:29', 4, 5, '2026-02-11 01:44:44'),
(190, 27, 'joao', 'chrome.exe', '2026-02-10 22:45:22', '2026-02-10 22:45:29', 5, 1, '2026-02-11 01:44:44'),
(191, 28, 'lucas', 'python3.12.exe', '2026-02-11 10:07:38', '2026-02-11 10:08:58', 17, 59, '2026-02-11 13:09:34'),
(192, 28, 'lucas', 'AnyDesk.exe', '2026-02-11 10:07:55', '2026-02-11 10:08:19', 1, 23, '2026-02-11 13:08:55'),
(193, 28, 'lucas', 'brave.exe', '2026-02-11 10:07:56', '2026-02-11 10:08:26', 6, 23, '2026-02-11 13:09:02'),
(194, 29, 'lucas', 'python3.12.exe', '2026-02-11 10:10:09', '2026-02-11 10:10:35', 1, 23, '2026-02-11 13:11:11'),
(195, 29, 'lucas', 'brave.exe', '2026-02-11 10:10:13', '2026-02-11 10:11:41', 65, 22, '2026-02-11 13:12:16'),
(196, 29, 'lucas', 'python3.12.exe', '2026-02-11 10:11:18', '2026-02-11 10:12:39', 1, 80, '2026-02-11 13:13:15'),
(197, 30, 'lucas', 'python3.12.exe', '2026-02-11 10:26:36', '2026-02-11 10:27:04', 3, 23, '2026-02-11 13:27:40'),
(198, 30, 'lucas', 'Code.exe', '2026-02-11 10:26:41', '2026-02-11 10:27:58', 53, 23, '2026-02-11 13:28:34'),
(199, 30, 'lucas', 'python3.12.exe', '2026-02-11 10:27:34', '2026-02-11 10:28:09', 1, 32, '2026-02-11 13:28:45'),
(200, 31, 'lucas', 'python3.12.exe', '2026-02-11 10:36:38', '2026-02-11 10:38:02', 61, 20, '2026-02-11 13:38:38'),
(201, 32, 'lucas', 'python3.12.exe', '2026-02-11 10:54:46', '2026-02-11 10:56:15', 70, 17, '2026-02-11 13:56:51'),
(202, 33, 'lucas', 'python3.12.exe', '2026-02-11 11:11:35', '2026-02-11 11:12:01', 1, 23, '2026-02-11 14:12:37'),
(203, 33, 'lucas', 'brave.exe', '2026-02-11 11:11:39', '2026-02-11 11:12:54', 52, 23, '2026-02-11 14:13:30'),
(204, 33, 'lucas', 'explorer.exe', '2026-02-11 11:12:30', '2026-02-11 11:12:55', 1, 23, '2026-02-11 14:13:31'),
(205, 33, 'lucas', 'python3.12.exe', '2026-02-11 11:12:32', '2026-02-11 11:16:40', 1, 248, '2026-02-11 14:17:16'),
(206, 33, 'lucas', 'SnippingTool.exe', '2026-02-11 11:13:09', '2026-02-11 11:13:34', 0, 24, '2026-02-11 14:14:10'),
(207, 34, 'lucas', 'python3.12.exe', '2026-02-11 11:17:32', '2026-02-11 11:18:04', 7, 23, '2026-02-11 14:18:40'),
(208, 34, 'lucas', 'Code.exe', '2026-02-11 11:17:41', '2026-02-11 11:19:01', 56, 23, '2026-02-11 14:19:37'),
(209, 34, 'lucas', 'python3.12.exe', '2026-02-11 11:18:37', '2026-02-11 11:19:26', 1, 49, '2026-02-11 14:20:02'),
(210, 35, 'lucas', 'python3.12.exe', '2026-02-11 11:31:39', NULL, 0, 0, '2026-02-11 14:32:15'),
(211, 36, 'lucas', 'python3.12.exe', '2026-02-11 11:36:29', NULL, 0, 0, '2026-02-11 14:37:05'),
(212, 37, 'lucas', 'python3.12.exe', '2026-02-11 11:43:00', NULL, 0, 0, '2026-02-11 14:43:36');

-- --------------------------------------------------------

--
-- Estrutura para tabela `cronometro_eventos_status`
--

CREATE TABLE `cronometro_eventos_status` (
  `id_evento` bigint NOT NULL,
  `id_sessao` bigint NOT NULL,
  `user_id` varchar(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `tipo_evento` enum('inicio','pausa','retorno','ocioso_inicio','ocioso_fim','finalizar','heartbeat') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `situacao` enum('trabalhando','ocioso','pausado') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `ocorrido_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `idle_segundos` int NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `cronometro_eventos_status`
--

INSERT INTO `cronometro_eventos_status` (`id_evento`, `id_sessao`, `user_id`, `tipo_evento`, `situacao`, `ocorrido_em`, `idle_segundos`) VALUES
(53, 23, 'lucas', 'inicio', 'trabalhando', '2026-02-09 15:09:07', 0),
(54, 23, 'lucas', 'pausa', 'pausado', '2026-02-09 15:10:03', 0),
(55, 23, 'lucas', 'heartbeat', 'pausado', '2026-02-09 15:10:07', 0),
(56, 23, 'lucas', 'finalizar', 'pausado', '2026-02-09 15:10:12', 0),
(57, 24, 'joao', 'inicio', 'trabalhando', '2026-02-10 22:29:42', 0),
(58, 24, 'joao', 'pausa', 'pausado', '2026-02-10 22:30:19', 0),
(59, 24, 'joao', 'pausa', 'pausado', '2026-02-10 22:30:27', 0),
(60, 24, 'joao', 'heartbeat', 'pausado', '2026-02-10 22:30:42', 0),
(61, 24, 'joao', 'retorno', 'trabalhando', '2026-02-10 22:31:35', 0),
(62, 24, 'joao', 'heartbeat', 'trabalhando', '2026-02-10 22:31:43', 0),
(63, 24, 'joao', 'pausa', 'pausado', '2026-02-10 22:31:44', 0),
(64, 24, 'joao', 'heartbeat', 'pausado', '2026-02-10 22:32:43', 0),
(65, 24, 'joao', 'finalizar', 'pausado', '2026-02-10 22:32:50', 0),
(66, 25, 'joao', 'inicio', 'trabalhando', '2026-02-10 22:33:44', 0),
(67, 25, 'joao', 'finalizar', 'pausado', '2026-02-10 22:34:25', 0),
(68, 26, 'joao', 'inicio', 'trabalhando', '2026-02-10 22:42:41', 0),
(69, 26, 'joao', 'finalizar', 'pausado', '2026-02-10 22:42:53', 0),
(70, 27, 'joao', 'inicio', 'trabalhando', '2026-02-10 22:45:17', 0),
(71, 27, 'joao', 'finalizar', 'pausado', '2026-02-10 22:45:30', 0),
(72, 28, 'lucas', 'inicio', 'trabalhando', '2026-02-11 10:07:38', 0),
(73, 28, 'lucas', 'pausa', 'pausado', '2026-02-11 10:08:06', 0),
(74, 28, 'lucas', 'heartbeat', 'pausado', '2026-02-11 10:08:39', 0),
(75, 28, 'lucas', 'finalizar', 'pausado', '2026-02-11 10:08:58', 0),
(76, 29, 'lucas', 'inicio', 'trabalhando', '2026-02-11 10:10:08', 0),
(77, 29, 'lucas', 'heartbeat', 'trabalhando', '2026-02-11 10:11:09', 31),
(78, 29, 'lucas', 'pausa', 'pausado', '2026-02-11 10:11:19', 0),
(79, 29, 'lucas', 'heartbeat', 'pausado', '2026-02-11 10:12:10', 38),
(80, 29, 'lucas', 'finalizar', 'pausado', '2026-02-11 10:12:40', 0),
(81, 30, 'lucas', 'inicio', 'trabalhando', '2026-02-11 10:26:35', 0),
(82, 30, 'lucas', 'pausa', 'pausado', '2026-02-11 10:27:36', 0),
(83, 30, 'lucas', 'heartbeat', 'pausado', '2026-02-11 10:27:37', 0),
(84, 30, 'lucas', 'finalizar', 'pausado', '2026-02-11 10:28:10', 0),
(85, 31, 'lucas', 'inicio', 'trabalhando', '2026-02-11 10:36:37', 0),
(86, 31, 'lucas', 'heartbeat', 'trabalhando', '2026-02-11 10:37:38', 60),
(87, 31, 'lucas', 'pausa', 'pausado', '2026-02-11 10:37:41', 0),
(88, 31, 'lucas', 'finalizar', 'pausado', '2026-02-11 10:38:02', 0),
(89, 32, 'lucas', 'inicio', 'trabalhando', '2026-02-11 10:54:45', 0),
(90, 32, 'lucas', 'heartbeat', 'trabalhando', '2026-02-11 10:55:46', 51),
(91, 32, 'lucas', 'pausa', 'pausado', '2026-02-11 10:55:57', 0),
(92, 32, 'lucas', 'finalizar', 'pausado', '2026-02-11 10:56:16', 0),
(93, 33, 'lucas', 'inicio', 'trabalhando', '2026-02-11 11:11:34', 0),
(94, 33, 'lucas', 'pausa', 'pausado', '2026-02-11 11:12:33', 0),
(95, 33, 'lucas', 'heartbeat', 'pausado', '2026-02-11 11:12:35', 0),
(96, 33, 'lucas', 'heartbeat', 'pausado', '2026-02-11 11:13:36', 13),
(97, 33, 'lucas', 'heartbeat', 'pausado', '2026-02-11 11:14:36', 73),
(98, 33, 'lucas', 'heartbeat', 'pausado', '2026-02-11 11:15:37', 134),
(99, 33, 'lucas', 'heartbeat', 'pausado', '2026-02-11 11:16:37', 0),
(100, 33, 'lucas', 'finalizar', 'pausado', '2026-02-11 11:16:40', 0),
(101, 34, 'lucas', 'inicio', 'trabalhando', '2026-02-11 11:17:31', 0),
(102, 34, 'lucas', 'heartbeat', 'trabalhando', '2026-02-11 11:18:32', 52),
(103, 34, 'lucas', 'pausa', 'pausado', '2026-02-11 11:18:38', 0),
(104, 34, 'lucas', 'finalizar', 'pausado', '2026-02-11 11:19:27', 0),
(105, 35, 'lucas', 'inicio', 'trabalhando', '2026-02-11 11:31:39', 0),
(106, 35, 'lucas', 'pausa', 'pausado', '2026-02-11 11:32:24', 0),
(107, 35, 'lucas', 'heartbeat', 'pausado', '2026-02-11 11:32:39', 0),
(108, 35, 'lucas', 'finalizar', 'pausado', '2026-02-11 11:32:48', 0),
(109, 36, 'lucas', 'inicio', 'trabalhando', '2026-02-11 11:36:29', 0),
(110, 36, 'lucas', 'finalizar', 'pausado', '2026-02-11 11:36:32', 0),
(111, 37, 'lucas', 'inicio', 'trabalhando', '2026-02-11 11:43:00', 0),
(112, 37, 'lucas', 'heartbeat', 'trabalhando', '2026-02-11 11:44:01', 0),
(113, 37, 'lucas', 'pausa', 'pausado', '2026-02-11 11:44:04', 0),
(114, 37, 'lucas', 'finalizar', 'pausado', '2026-02-11 11:44:26', 0),
(115, 38, 'lucas', 'inicio', 'trabalhando', '2026-02-11 13:43:55', 0),
(116, 38, 'lucas', 'pausa', 'pausado', '2026-02-11 13:44:39', 0),
(117, 38, 'lucas', 'heartbeat', 'pausado', '2026-02-11 13:44:55', 0),
(118, 38, 'lucas', 'finalizar', 'pausado', '2026-02-11 13:44:57', 0),
(119, 39, 'lucas', 'inicio', 'trabalhando', '2026-02-11 13:52:38', 0),
(120, 39, 'lucas', 'pausa', 'pausado', '2026-02-11 13:53:30', 0),
(121, 39, 'lucas', 'heartbeat', 'pausado', '2026-02-11 13:53:38', 1),
(122, 39, 'lucas', 'finalizar', 'pausado', '2026-02-11 13:54:16', 0),
(123, 40, 'lucas', 'inicio', 'trabalhando', '2026-02-11 14:03:37', 0),
(124, 40, 'lucas', 'retorno', 'trabalhando', '2026-02-11 14:03:53', 0),
(125, 40, 'lucas', 'retorno', 'trabalhando', '2026-02-11 14:03:55', 0),
(126, 40, 'lucas', 'retorno', 'trabalhando', '2026-02-11 14:03:56', 0),
(127, 40, 'lucas', 'pausa', 'pausado', '2026-02-11 14:04:10', 0),
(128, 40, 'lucas', 'heartbeat', 'pausado', '2026-02-11 14:04:38', 0),
(129, 40, 'lucas', 'finalizar', 'pausado', '2026-02-11 14:04:55', 0),
(130, 41, 'lucas', 'inicio', 'trabalhando', '2026-02-24 21:42:11', 0),
(131, 41, 'lucas', 'pausa', 'pausado', '2026-02-24 21:42:21', 0),
(132, 41, 'lucas', 'heartbeat', 'pausado', '2026-02-24 21:43:11', 0),
(133, 41, 'lucas', 'finalizar', 'pausado', '2026-02-24 21:44:02', 0),
(134, 42, 'lucas', 'inicio', 'trabalhando', '2026-03-23 20:04:35', 0),
(135, 42, 'lucas', 'pausa', 'pausado', '2026-03-23 20:05:07', 0),
(136, 42, 'lucas', 'retorno', 'trabalhando', '2026-03-23 20:05:11', 0),
(137, 42, 'lucas', 'pausa', 'pausado', '2026-03-23 20:05:15', 0),
(138, 42, 'lucas', 'heartbeat', 'pausado', '2026-03-23 20:05:35', 0),
(139, 42, 'lucas', 'finalizar', 'pausado', '2026-03-23 20:06:30', 0),
(140, 43, 'lucas', 'inicio', 'trabalhando', '2026-03-23 20:06:47', 0),
(141, 43, 'lucas', 'retorno', 'trabalhando', '2026-03-23 20:06:49', 0),
(142, 43, 'lucas', 'pausa', 'pausado', '2026-03-23 20:06:50', 0),
(143, 43, 'lucas', 'pausa', 'pausado', '2026-03-23 20:06:59', 0),
(144, 43, 'lucas', 'finalizar', 'pausado', '2026-03-23 20:07:04', 0),
(145, 44, 'lucas', 'inicio', 'trabalhando', '2026-03-23 20:19:49', 0),
(146, 45, 'lucas', 'inicio', 'trabalhando', '2026-03-23 20:33:02', 0),
(147, 45, 'lucas', 'retorno', 'trabalhando', '2026-03-23 20:44:02', 0),
(148, 45, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 20:45:01', 0),
(149, 45, 'lucas', 'pausa', 'pausado', '2026-03-23 20:45:19', 0),
(150, 45, 'lucas', 'finalizar', 'pausado', '2026-03-23 20:46:59', 0),
(151, 46, 'lucas', 'inicio', 'trabalhando', '2026-03-23 21:09:30', 0),
(152, 46, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:10:31', 0),
(153, 46, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:11:31', 1),
(154, 46, 'lucas', 'pausa', 'pausado', '2026-03-23 21:12:08', 0),
(155, 46, 'lucas', 'finalizar', 'pausado', '2026-03-23 21:12:48', 0),
(156, 47, 'lucas', 'inicio', 'trabalhando', '2026-03-23 21:14:19', 0),
(157, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:15:20', 0),
(158, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:16:20', 0),
(159, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:17:20', 0),
(160, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:18:20', 0),
(161, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:19:20', 0),
(162, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:20:21', 3),
(163, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:21:21', 12),
(164, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:22:21', 72),
(165, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:23:21', 23),
(166, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:24:21', 1),
(167, 47, 'lucas', 'pausa', 'pausado', '2026-03-23 21:25:08', 0),
(168, 47, 'lucas', 'retorno', 'trabalhando', '2026-03-23 21:26:20', 0),
(169, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:27:19', 0),
(170, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:28:19', 0),
(171, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:29:20', 0),
(172, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:30:21', 0),
(173, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:31:21', 0),
(174, 47, 'lucas', 'heartbeat', 'trabalhando', '2026-03-23 21:32:21', 0),
(175, 47, 'lucas', 'finalizar', 'pausado', '2026-03-23 21:32:38', 0),
(176, 48, 'joao', 'inicio', 'trabalhando', '2026-03-23 22:46:37', 0),
(177, 48, 'joao', 'heartbeat', 'trabalhando', '2026-03-23 22:47:37', 0),
(178, 48, 'joao', 'pausa', 'pausado', '2026-03-23 22:47:51', 0),
(179, 48, 'joao', 'retorno', 'trabalhando', '2026-03-23 22:47:59', 0),
(180, 48, 'joao', 'pausa', 'pausado', '2026-03-23 22:48:02', 0),
(181, 48, 'joao', 'finalizar', 'pausado', '2026-03-23 22:48:37', 0),
(182, 49, 'joao', 'inicio', 'trabalhando', '2026-03-23 22:57:25', 0),
(183, 49, 'joao', 'pausa', 'pausado', '2026-03-23 22:57:32', 0),
(184, 49, 'joao', 'retorno', 'trabalhando', '2026-03-23 22:58:52', 0),
(185, 49, 'joao', 'heartbeat', 'trabalhando', '2026-03-23 22:59:51', 0),
(186, 49, 'joao', 'heartbeat', 'trabalhando', '2026-03-23 23:00:51', 0),
(187, 49, 'joao', 'heartbeat', 'trabalhando', '2026-03-23 23:01:51', 0),
(188, 49, 'joao', 'heartbeat', 'trabalhando', '2026-03-23 23:02:51', 0),
(189, 49, 'joao', 'heartbeat', 'trabalhando', '2026-03-23 23:03:51', 0),
(190, 49, 'joao', 'heartbeat', 'trabalhando', '2026-03-23 23:04:51', 0),
(191, 49, 'joao', 'heartbeat', 'trabalhando', '2026-03-23 23:05:51', 0),
(192, 49, 'joao', 'heartbeat', 'trabalhando', '2026-03-23 23:06:51', 0),
(193, 49, 'joao', 'pausa', 'pausado', '2026-03-23 23:07:29', 0),
(194, 50, 'lucas', 'inicio', 'trabalhando', '2026-03-25 20:14:24', 0),
(195, 50, 'lucas', 'pausa', 'pausado', '2026-03-25 20:14:42', 0),
(196, 50, 'lucas', 'finalizar', 'pausado', '2026-03-25 20:23:50', 0),
(197, 51, 'lucas', 'inicio', 'trabalhando', '2026-03-25 20:25:48', 0),
(198, 51, 'lucas', 'retorno', 'trabalhando', '2026-03-25 20:27:40', 0),
(199, 51, 'lucas', 'pausa', 'pausado', '2026-03-25 20:27:58', 0),
(200, 51, 'lucas', 'retorno', 'trabalhando', '2026-03-25 20:30:26', 0),
(201, 51, 'lucas', 'pausa', 'pausado', '2026-03-25 20:30:42', 0),
(202, 51, 'lucas', 'finalizar', 'pausado', '2026-03-25 20:31:37', 0),
(203, 52, 'rafael', 'inicio', 'trabalhando', '2026-03-26 14:05:25', 0),
(204, 52, 'rafael', 'heartbeat', 'trabalhando', '2026-03-26 14:06:25', 0),
(205, 52, 'rafael', 'heartbeat', 'trabalhando', '2026-03-26 14:07:25', 2),
(206, 52, 'rafael', 'heartbeat', 'trabalhando', '2026-03-26 14:08:25', 0),
(207, 52, 'rafael', 'heartbeat', 'trabalhando', '2026-03-26 14:09:25', 0),
(208, 52, 'rafael', 'heartbeat', 'trabalhando', '2026-03-26 14:10:26', 0),
(209, 52, 'rafael', 'heartbeat', 'trabalhando', '2026-03-26 14:11:26', 0),
(210, 52, 'rafael', 'heartbeat', 'trabalhando', '2026-03-26 14:12:26', 0),
(211, 52, 'rafael', 'heartbeat', 'trabalhando', '2026-03-26 14:13:26', 0),
(212, 52, 'rafael', 'heartbeat', 'trabalhando', '2026-03-26 14:14:26', 0),
(213, 52, 'rafael', 'finalizar', 'pausado', '2026-03-26 14:14:28', 0),
(214, 53, 'rafael', 'inicio', 'trabalhando', '2026-03-26 14:16:08', 0),
(215, 53, 'rafael', 'pausa', 'pausado', '2026-03-26 14:16:29', 0),
(216, 53, 'rafael', 'finalizar', 'pausado', '2026-03-26 14:26:38', 0),
(217, 54, 'lucas', 'inicio', 'trabalhando', '2026-04-02 22:39:38', 0),
(218, 54, 'lucas', 'pausa', 'pausado', '2026-04-02 22:39:56', 0),
(219, 54, 'lucas', 'finalizar', 'pausado', '2026-04-02 22:41:54', 0),
(220, 55, 'lucas', 'inicio', 'trabalhando', '2026-04-02 22:51:59', 0),
(221, 55, 'lucas', 'pausa', 'pausado', '2026-04-02 22:52:11', 0),
(222, 55, 'lucas', 'finalizar', 'pausado', '2026-04-02 22:54:28', 0);

-- --------------------------------------------------------

--
-- Estrutura para tabela `cronometro_finalizacoes`
--

CREATE TABLE `cronometro_finalizacoes` (
  `id_finalizacao` bigint NOT NULL,
  `id_sessao` bigint NOT NULL,
  `user_id` varchar(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_atividade` int NOT NULL,
  `criado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `segundos_trabalhando` int NOT NULL DEFAULT '0',
  `segundos_ocioso` int NOT NULL DEFAULT '0',
  `segundos_pausado` int NOT NULL DEFAULT '0',
  `relatorio` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `cronometro_finalizacoes_subtarefas`
--

CREATE TABLE `cronometro_finalizacoes_subtarefas` (
  `id_item` bigint NOT NULL,
  `id_finalizacao` bigint NOT NULL,
  `id_subtarefa` bigint NOT NULL,
  `titulo_snapshot` varchar(220) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `concluida_snapshot` tinyint(1) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `cronometro_foco_janela`
--

CREATE TABLE `cronometro_foco_janela` (
  `id_foco` bigint NOT NULL,
  `id_sessao` bigint NOT NULL,
  `user_id` varchar(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `nome_app` varchar(180) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `titulo_janela` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inicio_em` datetime NOT NULL,
  `fim_em` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `cronometro_foco_janela`
--

INSERT INTO `cronometro_foco_janela` (`id_foco`, `id_sessao`, `user_id`, `nome_app`, `titulo_janela`, `inicio_em`, `fim_em`) VALUES
(58, 23, 'lucas', 'python3.12.exe', 'Cronômetro (Leve)', '2026-02-09 15:09:07', '2026-02-09 15:09:09'),
(59, 23, 'lucas', 'python3.12.exe', 'Cronômetro (Leve)', '2026-02-09 15:09:09', '2026-02-09 15:09:18'),
(60, 23, 'lucas', 'ms-teams.exe', 'Chat | Izabel Ramos | Microsoft Teams', '2026-02-09 15:09:18', '2026-02-09 15:09:20'),
(61, 23, 'lucas', 'ms-teams.exe', 'Chat | Allan Anderson da Silva | Microsoft Teams', '2026-02-09 15:09:20', '2026-02-09 15:09:35'),
(62, 23, 'lucas', 'ms-teams.exe', 'Chat | Vtex (Externo) | Microsoft Teams', '2026-02-09 15:09:35', '2026-02-09 15:09:38'),
(63, 23, 'lucas', 'chrome.exe', 'Lucas - Aba Gráficos Tempo Real - Google Chrome', '2026-02-09 15:09:39', '2026-02-09 15:09:40'),
(64, 23, 'lucas', 'chrome.exe', 'Todos os pedidos - Google Chrome', '2026-02-09 15:09:40', '2026-02-09 15:09:48'),
(65, 23, 'lucas', 'chrome.exe', 'Sem título - Google Chrome', '2026-02-09 15:09:49', '2026-02-09 15:09:50'),
(66, 23, 'lucas', 'chrome.exe', 'farmaconde.myvtex.com/admin/orders/1609021173828-01 - Google Chrome', '2026-02-09 15:09:50', '2026-02-09 15:09:51'),
(67, 23, 'lucas', 'chrome.exe', 'Todos os pedidos - Google Chrome', '2026-02-09 15:09:52', '2026-02-09 15:09:58'),
(68, 23, 'lucas', 'python3.12.exe', 'Cronômetro (Leve)', '2026-02-09 15:09:59', '2026-02-09 15:10:04'),
(69, 24, 'joao', 'cronometro.exe', 'Cronômetro (Leve)', '2026-02-10 22:29:42', '2026-02-10 22:29:44'),
(70, 24, 'joao', 'cronometro.exe', 'Cronômetro (Leve)', '2026-02-10 22:29:45', '2026-02-10 22:30:19'),
(71, 24, 'joao', 'cronometro.exe', 'Cronômetro (Leve)', '2026-02-10 22:31:35', '2026-02-10 22:31:44'),
(72, 25, 'joao', 'cronometro.exe', 'Cronômetro (Leve)', '2026-02-10 22:33:45', '2026-02-10 22:33:46'),
(73, 25, 'joao', 'cronometro.exe', 'Cronômetro (Leve)', '2026-02-10 22:33:47', '2026-02-10 22:33:55'),
(74, 25, 'joao', 'chrome.exe', 'Painel ADM · Cronômetro - Google Chrome', '2026-02-10 22:33:55', '2026-02-10 22:33:57'),
(75, 25, 'joao', 'chrome.exe', 'MOMENTOS FILMADOS SEGUNDOS ANTES DE ACIDENTES BIZARROS - Peter Reage - YouTube - Google Chrome', '2026-02-10 22:33:58', '2026-02-10 22:34:05'),
(76, 25, 'joao', 'chrome.exe', 'Nova guia - Google Chrome', '2026-02-10 22:34:05', '2026-02-10 22:34:07'),
(77, 25, 'joao', 'chrome.exe', 'xvideo - Pesquisa Google - Google Chrome', '2026-02-10 22:34:07', '2026-02-10 22:34:09'),
(78, 25, 'joao', 'chrome.exe', 'Vídeos pornô gratuitos - XVIDEOS.COM - Google Chrome', '2026-02-10 22:34:10', '2026-02-10 22:34:13'),
(79, 25, 'joao', 'chrome.exe', 'Painel ADM · Cronômetro - Google Chrome', '2026-02-10 22:34:13', '2026-02-10 22:34:18'),
(80, 25, 'joao', 'chrome.exe', 'MOMENTOS FILMADOS SEGUNDOS ANTES DE ACIDENTES BIZARROS - Peter Reage - YouTube - Google Chrome', '2026-02-10 22:34:18', '2026-02-10 22:34:20'),
(81, 25, 'joao', 'cronometro.exe', 'Cronômetro (Leve)', '2026-02-10 22:34:20', '2026-02-10 22:34:21'),
(82, 25, 'joao', 'cronometro.exe', 'Relatório', '2026-02-10 22:34:21', '2026-02-10 22:34:24'),
(83, 26, 'joao', 'cronometro.exe', 'Cronômetro (Leve)', '2026-02-10 22:42:41', '2026-02-10 22:42:43'),
(84, 26, 'joao', 'cronometro.exe', 'Cronômetro (Leve)', '2026-02-10 22:42:44', '2026-02-10 22:42:50'),
(85, 26, 'joao', 'cronometro.exe', 'Erro', '2026-02-10 22:42:50', '2026-02-10 22:42:51'),
(86, 26, 'joao', 'cronometro.exe', 'Cronômetro (Leve)', '2026-02-10 22:42:52', '2026-02-10 22:42:52'),
(87, 27, 'joao', 'cronometro.exe', 'Cronômetro (Leve)', '2026-02-10 22:45:17', '2026-02-10 22:45:19'),
(88, 27, 'joao', 'cronometro.exe', 'Cronômetro (Leve)', '2026-02-10 22:45:19', '2026-02-10 22:45:22'),
(89, 27, 'joao', 'chrome.exe', 'alanzoka - Twitch - Google Chrome', '2026-02-10 22:45:22', '2026-02-10 22:45:27'),
(90, 27, 'joao', 'cronometro.exe', 'Cronômetro (Leve)', '2026-02-10 22:45:28', '2026-02-10 22:45:29'),
(91, 28, 'lucas', 'python3.12.exe', 'Cronômetro (Leve)', '2026-02-11 10:07:38', '2026-02-11 10:07:40'),
(92, 28, 'lucas', 'python3.12.exe', 'Cronômetro (Leve)', '2026-02-11 10:07:40', '2026-02-11 10:07:54'),
(93, 28, 'lucas', 'AnyDesk.exe', 'AnyDesk', '2026-02-11 10:07:54', '2026-02-11 10:07:56'),
(94, 28, 'lucas', 'brave.exe', 'Painel ADM · Cronômetro - Brave', '2026-02-11 10:07:56', '2026-02-11 10:07:58'),
(95, 28, 'lucas', 'brave.exe', 'n8n.io - Workflow Automation - Brave', '2026-02-11 10:07:58', '2026-02-11 10:08:02'),
(96, 28, 'lucas', 'python3.12.exe', 'Cronômetro (Leve)', '2026-02-11 10:08:02', '2026-02-11 10:08:07'),
(97, 29, 'lucas', 'python3.12.exe', 'Cronômetro (Leve)', '2026-02-11 10:10:09', '2026-02-11 10:10:10'),
(98, 29, 'lucas', 'python3.12.exe', 'Cronômetro (Leve)', '2026-02-11 10:10:11', '2026-02-11 10:10:12'),
(99, 29, 'lucas', 'brave.exe', 'banco-painel-banco-phpmyadmin.cpgdmb.easypanel.host / banco_painel_banco / dados / declaracoes_dia_itens | phpMyAdmin 5.2.1 - Brave', '2026-02-11 10:10:13', '2026-02-11 10:11:17'),
(100, 29, 'lucas', 'python3.12.exe', 'Cronômetro (Leve)', '2026-02-11 10:11:17', '2026-02-11 10:11:20'),
(101, 30, 'lucas', 'python3.12.exe', 'Cronômetro (Leve)', '2026-02-11 10:26:36', '2026-02-11 10:26:37'),
(102, 30, 'lucas', 'python3.12.exe', 'Cronômetro (Leve)', '2026-02-11 10:26:38', '2026-02-11 10:26:40'),
(103, 30, 'lucas', 'Code.exe', 'app.py - Cronometro - Visual Studio Code', '2026-02-11 10:26:40', '2026-02-11 10:27:34'),
(104, 30, 'lucas', 'python3.12.exe', 'Cronômetro (Leve)', '2026-02-11 10:27:34', '2026-02-11 10:27:36'),
(105, 31, 'lucas', 'python3.12.exe', 'Cronômetro (Leve)', '2026-02-11 10:36:38', '2026-02-11 10:36:39'),
(106, 31, 'lucas', 'python3.12.exe', 'Cronômetro (Leve)', '2026-02-11 10:36:40', '2026-02-11 10:37:42'),
(107, 32, 'lucas', 'python3.12.exe', NULL, '2026-02-11 10:54:46', '2026-02-11 10:54:47'),
(108, 32, 'lucas', 'python3.12.exe', NULL, '2026-02-11 10:54:48', '2026-02-11 10:55:57'),
(109, 33, 'lucas', 'python3.12.exe', NULL, '2026-02-11 11:11:35', '2026-02-11 11:11:36'),
(110, 33, 'lucas', 'python3.12.exe', NULL, '2026-02-11 11:11:37', '2026-02-11 11:11:38'),
(111, 33, 'lucas', 'brave.exe', NULL, '2026-02-11 11:11:39', '2026-02-11 11:12:30'),
(112, 33, 'lucas', 'explorer.exe', NULL, '2026-02-11 11:12:30', '2026-02-11 11:12:31'),
(113, 33, 'lucas', 'python3.12.exe', NULL, '2026-02-11 11:12:32', '2026-02-11 11:12:33'),
(114, 34, 'lucas', 'python3.12.exe', NULL, '2026-02-11 11:17:31', '2026-02-11 11:17:33'),
(115, 34, 'lucas', 'python3.12.exe', NULL, '2026-02-11 11:17:34', '2026-02-11 11:17:40'),
(116, 34, 'lucas', 'Code.exe', NULL, '2026-02-11 11:17:40', '2026-02-11 11:18:37'),
(117, 34, 'lucas', 'python3.12.exe', NULL, '2026-02-11 11:18:37', '2026-02-11 11:18:38'),
(118, 35, 'lucas', 'python3.12.exe', NULL, '2026-02-11 11:31:39', '2026-02-11 11:31:40'),
(119, 35, 'lucas', 'python3.12.exe', NULL, '2026-02-11 11:31:41', '2026-02-11 11:32:25'),
(120, 36, 'lucas', 'python3.12.exe', NULL, '2026-02-11 11:36:29', '2026-02-11 11:36:30'),
(121, 36, 'lucas', 'python3.12.exe', NULL, '2026-02-11 11:36:31', '2026-02-11 11:36:31'),
(122, 37, 'lucas', 'python3.12.exe', NULL, '2026-02-11 11:43:00', '2026-02-11 11:43:02'),
(123, 37, 'lucas', 'python3.12.exe', NULL, '2026-02-11 11:43:02', '2026-02-11 11:44:05'),
(124, 38, 'lucas', 'python3.12.exe', NULL, '2026-02-11 13:43:55', '2026-02-11 13:44:39'),
(125, 39, 'lucas', 'python3.12.exe', NULL, '2026-02-11 13:52:39', '2026-02-11 13:52:39'),
(126, 39, 'lucas', 'python3.12.exe', NULL, '2026-02-11 13:52:40', '2026-02-11 13:52:55'),
(127, 39, 'lucas', 'Code.exe', NULL, '2026-02-11 13:52:56', '2026-02-11 13:53:28'),
(128, 39, 'lucas', 'python3.12.exe', NULL, '2026-02-11 13:53:28', '2026-02-11 13:53:30'),
(129, 40, 'lucas', 'python3.12.exe', NULL, '2026-02-11 14:03:38', '2026-02-11 14:03:38'),
(130, 40, 'lucas', 'python3.12.exe', NULL, '2026-02-11 14:03:39', NULL),
(131, 40, 'lucas', 'python3.12.exe', NULL, '2026-02-11 14:03:54', NULL),
(132, 40, 'lucas', 'python3.12.exe', NULL, '2026-02-11 14:03:55', NULL),
(133, 40, 'lucas', 'python3.12.exe', NULL, '2026-02-11 14:03:56', '2026-02-11 14:04:11'),
(134, 41, 'lucas', 'python3.12.exe', NULL, '2026-02-24 21:42:11', '2026-02-24 21:42:12'),
(135, 41, 'lucas', 'python3.12.exe', NULL, '2026-02-24 21:42:12', '2026-02-24 21:42:18'),
(136, 41, 'lucas', 'explorer.exe', NULL, '2026-02-24 21:42:18', '2026-02-24 21:42:19'),
(137, 41, 'lucas', 'python3.12.exe', NULL, '2026-02-24 21:42:19', '2026-02-24 21:42:22'),
(138, 42, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:04:36', '2026-03-23 20:04:36'),
(139, 42, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:04:37', '2026-03-23 20:05:07'),
(140, 42, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:05:11', '2026-03-23 20:05:16'),
(141, 43, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:06:48', '2026-03-23 20:06:48'),
(142, 43, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:06:49', NULL),
(143, 43, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:06:50', '2026-03-23 20:06:50'),
(144, 44, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:19:49', '2026-03-23 20:19:50'),
(145, 44, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:19:51', '2026-03-23 20:19:55'),
(146, 44, 'lucas', 'Code.exe', NULL, '2026-03-23 20:19:55', '2026-03-23 20:19:56'),
(147, 44, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:19:56', '2026-03-23 20:19:59'),
(148, 44, 'lucas', 'explorer.exe', NULL, '2026-03-23 20:20:00', '2026-03-23 20:20:00'),
(149, 44, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:20:01', '2026-03-23 20:20:02'),
(150, 44, 'lucas', 'Code.exe', NULL, '2026-03-23 20:20:03', '2026-03-23 20:20:03'),
(151, 44, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:20:04', '2026-03-23 20:20:08'),
(152, 45, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:33:02', '2026-03-23 20:33:04'),
(153, 45, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:33:04', '2026-03-23 20:33:43'),
(154, 45, 'lucas', 'Code.exe', NULL, '2026-03-23 20:33:44', NULL),
(155, 45, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:44:01', '2026-03-23 20:44:02'),
(156, 45, 'lucas', 'python3.12.exe', NULL, '2026-03-23 20:44:03', '2026-03-23 20:45:17'),
(157, 46, 'lucas', 'python3.12.exe', NULL, '2026-03-23 21:09:31', '2026-03-23 21:09:32'),
(158, 46, 'lucas', 'python3.12.exe', NULL, '2026-03-23 21:09:33', '2026-03-23 21:09:39'),
(159, 46, 'lucas', 'brave.exe', NULL, '2026-03-23 21:09:40', '2026-03-23 21:09:55'),
(160, 46, 'lucas', 'explorer.exe', NULL, '2026-03-23 21:09:55', '2026-03-23 21:09:56'),
(161, 46, 'lucas', 'python3.12.exe', NULL, '2026-03-23 21:09:56', '2026-03-23 21:09:57'),
(162, 46, 'lucas', 'xampp-control.exe', NULL, '2026-03-23 21:09:57', '2026-03-23 21:09:59'),
(163, 46, 'lucas', 'python3.12.exe', NULL, '2026-03-23 21:10:00', '2026-03-23 21:10:00'),
(164, 46, 'lucas', 'xampp-control.exe', NULL, '2026-03-23 21:10:01', '2026-03-23 21:10:36'),
(165, 46, 'lucas', 'brave.exe', NULL, '2026-03-23 21:10:36', '2026-03-23 21:10:43'),
(166, 46, 'lucas', 'explorer.exe', NULL, '2026-03-23 21:10:43', '2026-03-23 21:10:43'),
(167, 46, 'lucas', 'ApplicationFrameHost.exe', NULL, '2026-03-23 21:10:44', '2026-03-23 21:10:45'),
(168, 46, 'lucas', 'brave.exe', NULL, '2026-03-23 21:10:45', '2026-03-23 21:11:49'),
(169, 46, 'lucas', 'python3.12.exe', NULL, '2026-03-23 21:11:50', '2026-03-23 21:12:07'),
(170, 47, 'lucas', 'python3.12.exe', NULL, '2026-03-23 21:14:20', '2026-03-23 21:14:21'),
(171, 47, 'lucas', 'python3.12.exe', NULL, '2026-03-23 21:14:22', '2026-03-23 21:14:27'),
(172, 47, 'lucas', 'brave.exe', NULL, '2026-03-23 21:14:27', '2026-03-23 21:17:56'),
(173, 47, 'lucas', 'explorer.exe', NULL, '2026-03-23 21:17:56', '2026-03-23 21:18:01'),
(174, 47, 'lucas', 'Code.exe', NULL, '2026-03-23 21:18:01', '2026-03-23 21:18:04'),
(175, 47, 'lucas', 'brave.exe', NULL, '2026-03-23 21:18:04', '2026-03-23 21:25:01'),
(176, 47, 'lucas', 'explorer.exe', NULL, '2026-03-23 21:25:01', '2026-03-23 21:25:02'),
(177, 47, 'lucas', 'python3.12.exe', NULL, '2026-03-23 21:25:02', '2026-03-23 21:25:07'),
(178, 47, 'lucas', 'python3.12.exe', NULL, '2026-03-23 21:26:19', '2026-03-23 21:26:20'),
(179, 47, 'lucas', 'python3.12.exe', NULL, '2026-03-23 21:26:21', '2026-03-23 21:26:22'),
(180, 47, 'lucas', 'Code.exe', NULL, '2026-03-23 21:26:22', '2026-03-23 21:26:23'),
(181, 47, 'lucas', 'brave.exe', NULL, '2026-03-23 21:26:23', '2026-03-23 21:26:43'),
(182, 47, 'lucas', 'explorer.exe', NULL, '2026-03-23 21:26:44', '2026-03-23 21:26:44'),
(183, 47, 'lucas', 'python3.12.exe', NULL, '2026-03-23 21:26:44', '2026-03-23 21:26:46'),
(184, 47, 'lucas', 'brave.exe', NULL, '2026-03-23 21:26:46', '2026-03-23 21:27:26'),
(185, 47, 'lucas', 'python3.12.exe', NULL, '2026-03-23 21:27:26', '2026-03-23 21:27:32'),
(186, 47, 'lucas', 'brave.exe', NULL, '2026-03-23 21:27:32', '2026-03-23 21:27:56'),
(187, 47, 'lucas', 'explorer.exe', NULL, '2026-03-23 21:27:56', '2026-03-23 21:27:57'),
(188, 47, 'lucas', 'msedge.exe', NULL, '2026-03-23 21:27:57', '2026-03-23 21:27:58'),
(189, 47, 'lucas', 'brave.exe', NULL, '2026-03-23 21:27:59', '2026-03-23 21:28:30'),
(190, 47, 'lucas', 'explorer.exe', NULL, '2026-03-23 21:28:31', '2026-03-23 21:28:31'),
(191, 47, 'lucas', 'msedge.exe', NULL, '2026-03-23 21:28:31', '2026-03-23 21:28:32'),
(192, 47, 'lucas', 'brave.exe', NULL, '2026-03-23 21:28:32', '2026-03-23 21:29:26'),
(193, 47, 'lucas', 'explorer.exe', NULL, '2026-03-23 21:29:26', '2026-03-23 21:29:27'),
(194, 47, 'lucas', 'python3.12.exe', NULL, '2026-03-23 21:29:27', '2026-03-23 21:29:28'),
(195, 47, 'lucas', 'brave.exe', NULL, '2026-03-23 21:29:29', '2026-03-23 21:29:49'),
(196, 47, 'lucas', 'desconhecido', NULL, '2026-03-23 21:29:49', '2026-03-23 21:29:49'),
(197, 47, 'lucas', 'explorer.exe', NULL, '2026-03-23 21:29:50', '2026-03-23 21:29:54'),
(198, 47, 'lucas', 'brave.exe', NULL, '2026-03-23 21:29:54', '2026-03-23 21:29:57'),
(199, 47, 'lucas', 'explorer.exe', NULL, '2026-03-23 21:29:57', '2026-03-23 21:30:20'),
(200, 47, 'lucas', 'olk.exe', NULL, '2026-03-23 21:30:20', '2026-03-23 21:30:48'),
(201, 47, 'lucas', 'explorer.exe', NULL, '2026-03-23 21:30:48', '2026-03-23 21:30:49'),
(202, 47, 'lucas', 'brave.exe', NULL, '2026-03-23 21:30:49', '2026-03-23 21:32:25'),
(203, 47, 'lucas', 'explorer.exe', NULL, '2026-03-23 21:32:26', '2026-03-23 21:32:26'),
(204, 47, 'lucas', 'python3.12.exe', NULL, '2026-03-23 21:32:26', '2026-03-23 21:32:37'),
(205, 48, 'joao', 'CronometroLeve.exe', NULL, '2026-03-23 22:46:37', '2026-03-23 22:46:39'),
(206, 48, 'joao', 'CronometroLeve.exe', NULL, '2026-03-23 22:46:39', '2026-03-23 22:46:43'),
(207, 48, 'joao', 'chrome.exe', NULL, '2026-03-23 22:46:43', '2026-03-23 22:47:16'),
(208, 48, 'joao', 'CronometroLeve.exe', NULL, '2026-03-23 22:47:16', '2026-03-23 22:47:49'),
(209, 48, 'joao', 'CronometroLeve.exe', NULL, '2026-03-23 22:47:58', '2026-03-23 22:48:01'),
(210, 49, 'joao', 'CronometroLeve.exe', NULL, '2026-03-23 22:57:25', '2026-03-23 22:57:27'),
(211, 49, 'joao', 'CronometroLeve.exe', NULL, '2026-03-23 22:57:28', '2026-03-23 22:57:31'),
(212, 49, 'joao', 'CronometroLeve.exe', NULL, '2026-03-23 22:58:51', '2026-03-23 22:58:52'),
(213, 49, 'joao', 'CronometroLeve.exe', NULL, '2026-03-23 22:58:52', '2026-03-23 22:59:48'),
(214, 49, 'joao', 'soffice.bin', NULL, '2026-03-23 22:59:48', '2026-03-23 23:03:24'),
(215, 49, 'joao', 'CronometroLeve.exe', NULL, '2026-03-23 23:03:24', '2026-03-23 23:03:25'),
(216, 49, 'joao', 'chrome.exe', NULL, '2026-03-23 23:03:26', '2026-03-23 23:04:12'),
(217, 49, 'joao', 'SearchHost.exe', NULL, '2026-03-23 23:04:12', '2026-03-23 23:04:14'),
(218, 49, 'joao', 'StartMenuExperienceHost.exe', NULL, '2026-03-23 23:04:15', '2026-03-23 23:04:15'),
(219, 49, 'joao', 'explorer.exe', NULL, '2026-03-23 23:04:16', '2026-03-23 23:04:26'),
(220, 49, 'joao', 'chrome.exe', NULL, '2026-03-23 23:04:26', '2026-03-23 23:04:32'),
(221, 49, 'joao', 'Adobe Premiere Pro.exe', NULL, '2026-03-23 23:04:32', '2026-03-23 23:04:35'),
(222, 49, 'joao', 'explorer.exe', NULL, '2026-03-23 23:04:36', '2026-03-23 23:04:36'),
(223, 49, 'joao', 'chrome.exe', NULL, '2026-03-23 23:04:36', '2026-03-23 23:05:43'),
(224, 49, 'joao', 'soffice.bin', NULL, '2026-03-23 23:05:44', '2026-03-23 23:05:48'),
(225, 49, 'joao', 'chrome.exe', NULL, '2026-03-23 23:05:49', '2026-03-23 23:06:57'),
(226, 49, 'joao', 'soffice.bin', NULL, '2026-03-23 23:06:58', '2026-03-23 23:07:19'),
(227, 49, 'joao', 'chrome.exe', NULL, '2026-03-23 23:07:19', '2026-03-23 23:07:22'),
(228, 49, 'joao', 'CronometroLeve.exe', NULL, '2026-03-23 23:07:22', '2026-03-23 23:07:27'),
(229, 50, 'lucas', 'python3.12.exe', NULL, '2026-03-25 20:14:24', '2026-03-25 20:14:26'),
(230, 50, 'lucas', 'python3.12.exe', NULL, '2026-03-25 20:14:26', '2026-03-25 20:14:41'),
(231, 51, 'lucas', 'python3.12.exe', NULL, '2026-03-25 20:25:49', '2026-03-25 20:25:50'),
(232, 51, 'lucas', 'python3.12.exe', NULL, '2026-03-25 20:25:51', NULL),
(233, 51, 'lucas', 'python3.12.exe', NULL, '2026-03-25 20:27:39', '2026-03-25 20:27:40'),
(234, 51, 'lucas', 'python3.12.exe', NULL, '2026-03-25 20:27:41', '2026-03-25 20:27:57'),
(235, 51, 'lucas', 'python3.12.exe', NULL, '2026-03-25 20:30:25', '2026-03-25 20:30:41'),
(236, 52, 'rafael', 'CronometroLeve.exe', NULL, '2026-03-26 14:05:25', '2026-03-26 14:05:27'),
(237, 52, 'rafael', 'CronometroLeve.exe', NULL, '2026-03-26 14:05:27', '2026-03-26 14:05:36'),
(238, 52, 'rafael', 'chrome.exe', NULL, '2026-03-26 14:05:37', '2026-03-26 14:05:37'),
(239, 52, 'rafael', 'CronometroLeve.exe', NULL, '2026-03-26 14:05:37', '2026-03-26 14:05:39'),
(240, 52, 'rafael', 'chrome.exe', NULL, '2026-03-26 14:05:39', '2026-03-26 14:05:40'),
(241, 52, 'rafael', 'CronometroLeve.exe', NULL, '2026-03-26 14:05:40', '2026-03-26 14:05:48'),
(242, 52, 'rafael', 'chrome.exe', NULL, '2026-03-26 14:05:49', '2026-03-26 14:08:05'),
(243, 52, 'rafael', 'Lightshot.exe', NULL, '2026-03-26 14:08:05', '2026-03-26 14:08:07'),
(244, 52, 'rafael', 'chrome.exe', NULL, '2026-03-26 14:08:07', '2026-03-26 14:08:15'),
(245, 52, 'rafael', 'Lightshot.exe', NULL, '2026-03-26 14:08:15', '2026-03-26 14:08:17'),
(246, 52, 'rafael', 'chrome.exe', NULL, '2026-03-26 14:08:18', '2026-03-26 14:08:34'),
(247, 52, 'rafael', 'CronometroLeve.exe', NULL, '2026-03-26 14:08:34', '2026-03-26 14:08:35'),
(248, 52, 'rafael', 'chrome.exe', NULL, '2026-03-26 14:08:35', '2026-03-26 14:08:54'),
(249, 52, 'rafael', 'explorer.exe', NULL, '2026-03-26 14:08:54', '2026-03-26 14:08:55'),
(250, 52, 'rafael', 'Dolphin Anty.exe', NULL, '2026-03-26 14:08:55', '2026-03-26 14:09:05'),
(251, 52, 'rafael', 'chrome.exe', NULL, '2026-03-26 14:09:05', '2026-03-26 14:09:41'),
(252, 52, 'rafael', 'CronometroLeve.exe', NULL, '2026-03-26 14:09:42', '2026-03-26 14:09:43'),
(253, 52, 'rafael', 'Dolphin Anty.exe', NULL, '2026-03-26 14:09:43', '2026-03-26 14:09:44'),
(254, 52, 'rafael', 'chrome.exe', NULL, '2026-03-26 14:09:45', '2026-03-26 14:10:01'),
(255, 52, 'rafael', 'explorer.exe', NULL, '2026-03-26 14:10:02', '2026-03-26 14:10:02'),
(256, 52, 'rafael', 'CronometroLeve.exe', NULL, '2026-03-26 14:10:02', '2026-03-26 14:11:54'),
(257, 52, 'rafael', 'explorer.exe', NULL, '2026-03-26 14:11:54', '2026-03-26 14:11:55'),
(258, 52, 'rafael', 'chrome.exe', NULL, '2026-03-26 14:11:55', '2026-03-26 14:11:56'),
(259, 52, 'rafael', 'CronometroLeve.exe', NULL, '2026-03-26 14:11:56', '2026-03-26 14:12:22'),
(260, 52, 'rafael', 'dwm.exe', NULL, '2026-03-26 14:12:22', '2026-03-26 14:12:24'),
(261, 52, 'rafael', 'CronometroLeve.exe', NULL, '2026-03-26 14:12:24', '2026-03-26 14:14:28'),
(262, 53, 'rafael', 'CronometroLeve.exe', NULL, '2026-03-26 14:16:08', '2026-03-26 14:16:10'),
(263, 53, 'rafael', 'CronometroLeve.exe', NULL, '2026-03-26 14:16:11', '2026-03-26 14:16:15'),
(264, 53, 'rafael', 'chrome.exe', NULL, '2026-03-26 14:16:15', '2026-03-26 14:16:24'),
(265, 53, 'rafael', 'CronometroLeve.exe', NULL, '2026-03-26 14:16:25', '2026-03-26 14:16:28'),
(266, 54, 'lucas', 'python3.12.exe', NULL, '2026-04-02 22:39:39', '2026-04-02 22:39:40'),
(267, 54, 'lucas', 'python3.12.exe', NULL, '2026-04-02 22:39:41', '2026-04-02 22:39:55'),
(268, 55, 'lucas', 'python3.12.exe', NULL, '2026-04-02 22:51:59', '2026-04-02 22:52:01'),
(269, 55, 'lucas', 'python3.12.exe', NULL, '2026-04-02 22:52:02', '2026-04-02 22:52:10');

-- --------------------------------------------------------

--
-- Estrutura para tabela `cronometro_relatorios`
--

CREATE TABLE `cronometro_relatorios` (
  `id_relatorio` int NOT NULL,
  `id_sessao` int NOT NULL,
  `user_id` varchar(80) NOT NULL,
  `id_atividade` int NOT NULL,
  `relatorio` text NOT NULL,
  `segundos_total` int NOT NULL DEFAULT '0',
  `segundos_trabalhando` int NOT NULL DEFAULT '0',
  `segundos_ocioso` int NOT NULL DEFAULT '0',
  `segundos_pausado` int NOT NULL DEFAULT '0',
  `criado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Despejando dados para a tabela `cronometro_relatorios`
--

INSERT INTO `cronometro_relatorios` (`id_relatorio`, `id_sessao`, `user_id`, `id_atividade`, `relatorio`, `segundos_total`, `segundos_trabalhando`, `segundos_ocioso`, `segundos_pausado`, `criado_em`) VALUES
(15, 23, 'lucas', 3, 'testestestes', 63, 54, 0, 8, '2026-02-09 15:10:12'),
(16, 24, 'joao', 4, 'teste teste teste', 185, 43, 0, 142, '2026-02-10 22:32:50'),
(17, 25, 'joao', 4, 'teste 1', 38, 38, 0, 0, '2026-02-10 22:34:25'),
(18, 26, 'joao', 4, 'Encerrado ao fechar a janela (finalização automática).', 9, 9, 0, 0, '2026-02-10 22:42:53'),
(19, 27, 'joao', 4, 'Encerrado ao fechar a janela (finalização automática).', 9, 9, 0, 0, '2026-02-10 22:45:30'),
(20, 28, 'lucas', 3, 'Relatório do dia salvo em declaracoes_dia_itens (2026-02-11). Declarado=00:00', 77, 25, 0, 51, '2026-02-11 10:08:59'),
(21, 29, 'lucas', 3, 'Relatório do dia salvo em declaracoes_dia_itens (2026-02-11). Declarado=00:00', 148, 67, 0, 80, '2026-02-11 10:12:40'),
(22, 30, 'lucas', 3, 'Relatório do dia salvo em declaracoes_dia_itens (2026-02-11). Atividade=3 Declarado=00:02', 90, 57, 0, 0, '2026-02-11 10:28:10'),
(23, 31, 'lucas', 3, 'Relatório do dia (2026-02-11), atividade #3\n- 1:30 | video tal tal tal tal | taaaaaa', 82, 61, 0, 20, '2026-02-11 10:38:03'),
(24, 32, 'lucas', 3, 'Relatório do dia (2026-02-11), atividade #3\n- 01:40 | canal tal tal tal | tqal tjdawjdwads', 87, 70, 0, 17, '2026-02-11 10:56:16'),
(25, 33, 'lucas', 3, 'Encerrado ao fechar a janela (finalização automática).', 304, 56, 0, 248, '2026-02-11 11:16:41'),
(26, 34, 'lucas', 3, 'Relatório do dia (2026-02-11), atividade #3\n- 00:01 | tal atal oicsa tal | tal coisassa', 113, 64, 0, 49, '2026-02-11 11:19:27'),
(27, 35, 'lucas', 3, 'Relatório do dia (2026-02-11), atividade #3\n- 00:00:44 | fiz tal coisa sentei a madera | manderei legal', 68, 44, 0, 0, '2026-02-11 11:32:49'),
(28, 36, 'lucas', 3, 'Encerrado ao fechar a janela (finalização automática).', 1, 1, 0, 0, '2026-02-11 11:36:32'),
(29, 37, 'lucas', 3, 'Relatório do dia (2026-02-11), atividade #3\n- 00:01:03 | aeeeee consegui la | consegui la', 84, 63, 0, 0, '2026-02-11 11:44:26'),
(30, 38, 'lucas', 3, 'Encerrado ao fechar a janela (finalização automática).', 42, 42, 0, 0, '2026-02-11 13:44:58'),
(31, 39, 'lucas', 3, 'Relatório do dia (2026-02-11), atividade #3\n- 00:00:50 | titulo titulo titulo | legal legal legal', 50, 50, 0, 0, '2026-02-11 13:54:16'),
(32, 40, 'lucas', 3, 'Relatório do dia (2026-02-11), atividade #3\n- 00:00:32 | trablho tal tal tal tal tal | tal tal tal tal tal', 32, 32, 0, 45, '2026-02-11 14:04:56'),
(33, 41, 'lucas', 3, 'Encerrado ao fechar a janela (finalização automática).', 10, 10, 0, 100, '2026-02-24 21:44:02'),
(34, 42, 'lucas', 3, 'Relatório do dia (2026-03-23), atividade #3\n- 00:00:35 | editei video tal tal tal', 35, 35, 0, 78, '2026-03-23 20:06:30'),
(35, 43, 'lucas', 3, 'Encerrado ao fechar a janela (finalização automática).', 2, 2, 0, 14, '2026-03-23 20:07:05'),
(36, 45, 'lucas', 3, 'Relatório do dia (2026-03-23), atividade #3\n- 00:02:00 | tes', 120, 120, 0, 0, '2026-03-23 20:47:00'),
(37, 46, 'lucas', 3, 'Relatório do dia (2026-03-23), atividade #3\n- 00:02:36 | wadwadwa', 156, 156, 0, 0, '2026-03-23 21:12:49'),
(38, 47, 'lucas', 3, 'Relatório do dia (2026-03-23), atividade #3\n- 00:16:55 | dwadwadwa', 1025, 1025, 0, 0, '2026-03-23 21:32:38'),
(39, 48, 'joao', 4, 'Relatório do dia (2026-03-23), atividade #4\n- 00:01:00 | asd', 75, 75, 0, 0, '2026-03-23 22:48:38'),
(40, 50, 'lucas', 3, 'Relatório do dia (2026-03-25), atividade #3\n- 00:00:16 | mapeamento | Canal: canal tal tal | tal tal tal', 16, 16, 0, 0, '2026-03-25 20:23:51'),
(41, 51, 'lucas', 3, 'Relatório do dia (2026-03-25), atividade #3\n- 00:00:38 | adwadadwwww | Canal: ddddddd | aaaaaaa', 38, 38, 0, 0, '2026-03-25 20:31:37'),
(42, 52, 'rafael', 4, 'Relatório do dia (2026-03-26), atividade #4\n- 00:05:00 | Video 1 | Canal: Brian Cox', 542, 542, 0, 0, '2026-03-26 14:14:29'),
(43, 53, 'rafael', 4, 'Relatório do dia (2026-03-26), atividade #4\n- 00:03:00 | Video 1 | Canal: Brian Cox\n- 00:06:00 | Teste | Canal: asdasd | asdasd', 19, 19, 0, 0, '2026-03-26 14:26:39'),
(44, 54, 'lucas', 3, 'Relatório do dia (2026-04-02), atividade #3\n- 00:00:14 | dadwad | Canal: dadadw | dwadwad', 16, 16, 0, 0, '2026-04-02 22:41:54'),
(45, 55, 'lucas', 3, 'Relatório do dia (2026-04-02), atividade #3\n- 00:00:14 | dadwad | Canal: dadadw | dwadwad', 11, 11, 0, 0, '2026-04-02 22:54:28');

-- --------------------------------------------------------

--
-- Estrutura para tabela `cronometro_sessoes`
--

CREATE TABLE `cronometro_sessoes` (
  `id_sessao` bigint NOT NULL,
  `user_id` varchar(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `token_sessao` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `maquina_nome` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sistema` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `versao_app` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iniciado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `finalizado_em` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `cronometro_sessoes`
--

INSERT INTO `cronometro_sessoes` (`id_sessao`, `user_id`, `token_sessao`, `maquina_nome`, `sistema`, `versao_app`, `iniciado_em`, `finalizado_em`) VALUES
(23, 'lucas', '24780ad9b7c14123887e88e23a7ad48f', 'FCNTB-TI056', 'Windows 11', 'v1', '2026-02-09 15:09:07', '2026-02-09 15:10:12'),
(24, 'joao', '88b3748bd04d4d958c52a82ce3bedbb3', 'DESKTOP-N2RR475', 'Windows 11', 'v1', '2026-02-10 22:29:42', '2026-02-10 22:32:50'),
(25, 'joao', 'd2d289e74e36471c9f109e7e57d99b3d', 'DESKTOP-N2RR475', 'Windows 11', 'v1', '2026-02-10 22:33:44', '2026-02-10 22:34:25'),
(26, 'joao', '185cb23b991e458e93126b3120b6b7cf', 'DESKTOP-N2RR475', 'Windows 11', 'v1', '2026-02-10 22:42:41', '2026-02-10 22:42:53'),
(27, 'joao', 'd7c4bc5c510f493389e7e39e1d27612e', 'DESKTOP-N2RR475', 'Windows 11', 'v1', '2026-02-10 22:45:17', '2026-02-10 22:45:30'),
(28, 'lucas', '643d7f6f719e45c09378402686df95e6', 'lucas', 'Windows 11', 'v1', '2026-02-11 10:07:38', '2026-02-11 10:08:59'),
(29, 'lucas', '618e8704d8784188a1b63a4f4ef3ce5a', 'lucas', 'Windows 11', 'v1', '2026-02-11 10:10:08', '2026-02-11 10:12:40'),
(30, 'lucas', 'ac06512bd9004eddbf98990b76006bf4', 'lucas', 'Windows 11', 'v1', '2026-02-11 10:26:35', '2026-02-11 10:28:10'),
(31, 'lucas', '412c2f8abc404e05a35175792b8ac610', 'lucas', 'Windows 11', 'v1', '2026-02-11 10:36:37', '2026-02-11 10:38:02'),
(32, 'lucas', '322814cf8025468d8bf8855454cd62b8', 'lucas', 'Windows 11', 'v1', '2026-02-11 10:54:45', '2026-02-11 10:56:16'),
(33, 'lucas', '1837425ce1f74c7787510aa249a0bccd', 'lucas', 'Windows 11', 'v1', '2026-02-11 11:11:34', '2026-02-11 11:16:40'),
(34, 'lucas', 'dd1610ed5de64b718e229c50f108953b', 'lucas', 'Windows 11', 'v1', '2026-02-11 11:17:31', '2026-02-11 11:19:27'),
(35, 'lucas', 'feede45beb024839a3d50d9292414b22', 'lucas', 'Windows 11', 'v1', '2026-02-11 11:31:38', '2026-02-11 11:32:48'),
(36, 'lucas', 'e275d55fee214809a9a18f35c84c1ce4', 'lucas', 'Windows 11', 'v1', '2026-02-11 11:36:28', '2026-02-11 11:36:32'),
(37, 'lucas', 'f06b1f6d7d4a4404b961f912a43af30f', 'lucas', 'Windows 11', 'v1', '2026-02-11 11:43:00', '2026-02-11 11:44:26'),
(38, 'lucas', '0ae248a8cf59463aaed54a87b24213b6', 'lucas', 'Windows 11', 'v1', '2026-02-11 13:43:55', '2026-02-11 13:44:57'),
(39, 'lucas', 'a57ca845d8634a7390712c6128258568', 'lucas', 'Windows 11', 'v1', '2026-02-11 13:52:38', '2026-02-11 13:54:16'),
(40, 'lucas', '2c88c166cf3c493e8f398988ca8d5412', 'lucas', 'Windows 11', 'v1', '2026-02-11 14:03:37', '2026-02-11 14:04:55'),
(41, 'lucas', 'dd6509f77557436b907882abe80cd754', 'lucas', 'Windows 11', 'v1', '2026-02-24 21:42:10', '2026-02-24 21:44:02'),
(42, 'lucas', 'c4f9a16dee55447082c0d2c8b01d566e', 'lucas', 'Windows 11', 'v1', '2026-03-23 20:04:35', '2026-03-23 20:06:30'),
(43, 'lucas', 'b95c350859b4462e94b9805f456f88b8', 'lucas', 'Windows 11', 'v1', '2026-03-23 20:06:47', '2026-03-23 20:07:04'),
(44, 'lucas', 'f837b243489f447e9d387b1e8b633321', 'lucas', 'Windows 11', 'v2', '2026-03-23 20:19:49', '2026-03-23 23:27:09'),
(45, 'lucas', '8180424475a849068890cc5e52b8ff9c', 'lucas', 'Windows 11', 'v2.1', '2026-03-23 20:33:01', '2026-03-23 20:46:59'),
(46, 'lucas', '8f64d415b0f9445381793f114954bb66', 'lucas', 'Windows 11', 'v2.1', '2026-03-23 21:09:30', '2026-03-23 21:12:49'),
(47, 'lucas', 'b8297eccf5744c0eb42ee6e1a98919dd', 'lucas', 'Windows 11', 'v2.1', '2026-03-23 21:14:19', '2026-03-23 21:32:38'),
(48, 'joao', '05581ece0d1b47ca8628eba0347e74dd', 'DESKTOP-N2RR475', 'Windows 11', 'v2.1', '2026-03-23 22:46:36', '2026-03-23 22:48:37'),
(49, 'joao', 'da185a865b6c4d52806422eec4c40c40', 'DESKTOP-N2RR475', 'Windows 11', 'v2.1', '2026-03-23 22:57:25', NULL),
(50, 'lucas', '73cde2dc2b8641b689b703ffbb693fc6', 'lucas', 'Windows 11', 'v2.1', '2026-03-25 20:14:24', '2026-03-25 20:23:51'),
(51, 'lucas', 'e3a53e536da84b8cbde6924a21b6ab8f', 'lucas', 'Windows 11', 'v2.1', '2026-03-25 20:25:48', '2026-03-25 20:31:37'),
(52, 'rafael', 'b726c585c6654dad822bf13302bf0a4e', 'DESKTOP-N2RR475', 'Windows 11', 'v2.1', '2026-03-26 14:05:25', '2026-03-26 14:14:29'),
(53, 'rafael', '6c318b8717714d4a926785a7c63b3a46', 'DESKTOP-N2RR475', 'Windows 11', 'v2.1', '2026-03-26 14:16:08', '2026-03-26 14:26:39'),
(54, 'lucas', 'a9373fe1f12e43cfac8f91a3593c0100', 'lucas', 'Windows 11', 'v2.1', '2026-04-02 22:39:38', '2026-04-02 22:41:54'),
(55, 'lucas', 'aeea547ab39d4d5589772a6090ba1fe2', 'lucas', 'Windows 11', 'v2.1', '2026-04-02 22:51:59', '2026-04-02 22:54:28');

-- --------------------------------------------------------

--
-- Estrutura para tabela `declaracoes_dia_itens`
--

CREATE TABLE `declaracoes_dia_itens` (
  `id_item` bigint NOT NULL,
  `user_id` varchar(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `referencia_data` date NOT NULL,
  `id_atividade` int NOT NULL,
  `id_subtarefa` bigint DEFAULT NULL,
  `segundos_declarados` int NOT NULL DEFAULT '0',
  `o_que_fez` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `canal_entrega` varchar(180) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observacao` varchar(600) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `criado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `declaracoes_dia_itens`
--

INSERT INTO `declaracoes_dia_itens` (`id_item`, `user_id`, `referencia_data`, `id_atividade`, `id_subtarefa`, `segundos_declarados`, `o_que_fez`, `canal_entrega`, `observacao`, `criado_em`, `atualizado_em`) VALUES
(2, 'lucas', '2026-02-11', 3, NULL, 60, 'tal atal oicsa tal', NULL, 'tal coisassa', '2026-02-11 14:20:02', '2026-02-11 14:20:02'),
(3, 'lucas', '2026-02-11', 3, NULL, 44, 'fiz tal coisa sentei a madera', NULL, 'manderei legal', '2026-02-11 14:33:24', '2026-02-11 14:33:24'),
(4, 'lucas', '2026-02-11', 3, NULL, 63, 'aeeeee consegui la', NULL, 'consegui la', '2026-02-11 14:45:01', '2026-02-11 14:45:01'),
(5, 'lucas', '2026-02-11', 3, NULL, 50, 'titulo titulo titulo', NULL, 'legal legal legal', '2026-02-11 16:54:51', '2026-02-11 16:54:51'),
(6, 'lucas', '2026-02-11', 3, NULL, 32, 'trablho tal tal tal tal tal', NULL, 'tal tal tal tal tal', '2026-02-11 17:05:30', '2026-02-11 17:05:30'),
(7, 'lucas', '2026-03-23', 3, NULL, 35, 'editei video tal tal tal', NULL, NULL, '2026-03-23 23:06:34', '2026-03-23 23:06:34'),
(8, 'lucas', '2026-03-23', 3, NULL, 120, 'tes', NULL, NULL, '2026-03-23 23:47:03', '2026-03-23 23:47:03'),
(9, 'lucas', '2026-03-23', 3, NULL, 156, 'wadwadwa', NULL, NULL, '2026-03-24 00:12:52', '2026-03-24 00:12:52'),
(10, 'lucas', '2026-03-23', 3, NULL, 1015, 'dwadwadwa', NULL, NULL, '2026-03-24 00:32:41', '2026-03-24 00:32:41'),
(11, 'joao', '2026-03-23', 4, NULL, 60, 'asd', NULL, NULL, '2026-03-24 01:46:17', '2026-03-24 01:46:17'),
(14, 'lucas', '2026-03-25', 3, 7, 38, 'adwadadwwww', 'ddddddd', 'aaaaaaa', '2026-03-25 23:31:33', '2026-03-25 23:31:33'),
(15, 'rafael', '2026-03-26', 4, 8, 180, 'Video 1', 'Brian Cox', NULL, '2026-03-26 17:09:54', '2026-03-26 17:16:16'),
(16, 'rafael', '2026-03-26', 4, 10, 360, 'Teste', 'asdasd', 'asdasd', '2026-03-26 17:17:05', '2026-03-26 17:17:30'),
(17, 'lucas', '2026-04-02', 3, 11, 14, 'dadwad', 'dadadw', 'dwadwad', '2026-04-03 01:41:51', '2026-04-03 01:41:51');

-- --------------------------------------------------------

--
-- Estrutura para tabela `Pagamentos`
--

CREATE TABLE `Pagamentos` (
  `id_pagamento` int NOT NULL,
  `id_usuario` int NOT NULL,
  `data_pagamento` date NOT NULL,
  `referencia_inicio` date DEFAULT NULL,
  `referencia_fim` date DEFAULT NULL,
  `travado_ate_data` date DEFAULT NULL,
  `valor` decimal(10,2) NOT NULL,
  `observacao` varchar(255) DEFAULT NULL,
  `criado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `registros_tempo`
--

CREATE TABLE `registros_tempo` (
  `id_registro` bigint NOT NULL,
  `user_id` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `situacao` enum('trabalhando','ocioso','pausado') COLLATE utf8mb4_unicode_ci NOT NULL,
  `segundos` int NOT NULL DEFAULT '0',
  `referencia_data` date NOT NULL,
  `referencia_mes` char(7) COLLATE utf8mb4_unicode_ci NOT NULL,
  `criado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `registros_tempo`
--

INSERT INTO `registros_tempo` (`id_registro`, `user_id`, `situacao`, `segundos`, `referencia_data`, `referencia_mes`, `criado_em`) VALUES
(1, 'lucas', 'trabalhando', 25, '2026-02-11', '2026-02', '2026-02-11 10:08:06'),
(2, 'lucas', 'pausado', 3, '2026-02-11', '2026-02', '2026-02-11 10:08:08'),
(3, 'lucas', 'pausado', 31, '2026-02-11', '2026-02', '2026-02-11 10:08:39'),
(4, 'lucas', 'pausado', 17, '2026-02-11', '2026-02', '2026-02-11 10:08:58'),
(5, 'lucas', 'trabalhando', 29, '2026-02-11', '2026-02', '2026-02-11 10:10:39'),
(6, 'lucas', 'trabalhando', 30, '2026-02-11', '2026-02', '2026-02-11 10:11:09'),
(7, 'lucas', 'trabalhando', 8, '2026-02-11', '2026-02', '2026-02-11 10:11:19'),
(8, 'lucas', 'pausado', 21, '2026-02-11', '2026-02', '2026-02-11 10:11:39'),
(9, 'lucas', 'pausado', 31, '2026-02-11', '2026-02', '2026-02-11 10:12:10'),
(10, 'lucas', 'pausado', 28, '2026-02-11', '2026-02', '2026-02-11 10:12:39'),
(11, 'lucas', 'trabalhando', 29, '2026-02-11', '2026-02', '2026-02-11 10:27:06'),
(12, 'lucas', 'trabalhando', 28, '2026-02-11', '2026-02', '2026-02-11 10:27:36'),
(13, 'lucas', 'pausado', 1, '2026-02-11', '2026-02', '2026-02-11 10:27:37'),
(14, 'lucas', 'pausado', 31, '2026-02-11', '2026-02', '2026-02-11 10:28:06'),
(15, 'lucas', 'trabalhando', 29, '2026-02-11', '2026-02', '2026-02-11 10:37:08'),
(16, 'lucas', 'trabalhando', 30, '2026-02-11', '2026-02', '2026-02-11 10:37:38'),
(17, 'lucas', 'trabalhando', 2, '2026-02-11', '2026-02', '2026-02-11 10:37:41'),
(18, 'lucas', 'pausado', 20, '2026-02-11', '2026-02', '2026-02-11 10:38:02');

-- --------------------------------------------------------

--
-- Estrutura para tabela `usuarios`
--

CREATE TABLE `usuarios` (
  `id_usuario` int NOT NULL,
  `user_id` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nome_exibicao` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nivel` enum('iniciante','intermediario','avancado') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'intermediario',
  `valor_hora` decimal(10,2) NOT NULL DEFAULT '0.00',
  `chave` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status_conta` enum('ativa','inativa','bloqueada') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ativa',
  `criado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `usuarios`
--

INSERT INTO `usuarios` (`id_usuario`, `user_id`, `nome_exibicao`, `nivel`, `valor_hora`, `chave`, `status_conta`, `criado_em`, `atualizado_em`) VALUES
(1, 'lucas', 'lucas', 'intermediario', 40.00, 'rk_7a33d4_444ebc_d3554d', 'ativa', '2026-02-03 18:37:53', '2026-02-04 14:30:31'),
(2, 'joao', 'Joao', 'intermediario', 10.00, 'rk_d6d50b_e10acd_5c4c15', 'ativa', '2026-02-11 01:16:04', '2026-02-11 01:16:04'),
(3, 'rafael', 'rafael', 'intermediario', 10.00, 'rk_0d355d_889372_7e3135', 'ativa', '2026-03-26 17:01:59', '2026-03-26 17:01:59');

-- --------------------------------------------------------

--
-- Estrutura para tabela `usuarios_status_atual`
--

CREATE TABLE `usuarios_status_atual` (
  `id_status` int NOT NULL,
  `user_id` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `situacao` enum('trabalhando','ocioso','pausado') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ocioso',
  `atividade` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `inicio_em` datetime DEFAULT NULL,
  `ultimo_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `segundos_pausado` int NOT NULL DEFAULT '0',
  `apps_json` json DEFAULT NULL,
  `atualizado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `usuarios_status_atual`
--

INSERT INTO `usuarios_status_atual` (`id_status`, `user_id`, `situacao`, `atividade`, `inicio_em`, `ultimo_em`, `segundos_pausado`, `apps_json`, `atualizado_em`) VALUES
(1, 'lucas', 'pausado', '', NULL, '2026-04-02 22:54:29', 0, '{\"abertos\": [], \"em_foco\": {\"nome_app\": \"desconhecido\", \"titulo_janela\": \"\"}}', '2026-04-03 01:54:35'),
(40, 'joao', 'pausado', 'Editor de video (aberta)', '2026-03-23 22:57:25', '2026-03-26 13:44:21', 0, '{\"abertos\": [], \"em_foco\": {\"nome_app\": \"desconhecido\", \"titulo_janela\": \"\"}}', '2026-03-26 16:41:55'),
(84, 'rafael', 'pausado', '', NULL, '2026-03-26 14:26:39', 0, '{\"abertos\": [], \"em_foco\": {\"nome_app\": \"desconhecido\", \"titulo_janela\": \"\"}}', '2026-03-26 17:24:14');

--
-- Índices para tabelas despejadas
--

--
-- Índices de tabela `atividades`
--
ALTER TABLE `atividades`
  ADD PRIMARY KEY (`id_atividade`),
  ADD KEY `idx_atividades_status` (`status`),
  ADD KEY `idx_atividades_criado_em` (`criado_em`);

--
-- Índices de tabela `atividades_subtarefas`
--
ALTER TABLE `atividades_subtarefas`
  ADD PRIMARY KEY (`id_subtarefa`),
  ADD KEY `idx_atividade_user` (`id_atividade`,`user_id`),
  ADD KEY `idx_user_concluida` (`user_id`,`concluida`),
  ADD KEY `idx_subtarefas_user_data_atividade` (`user_id`,`referencia_data`,`id_atividade`),
  ADD KEY `idx_subtarefas_id_pagamento` (`id_pagamento`),
  ADD KEY `idx_subtarefas_id_sessao` (`id_sessao`),
  ADD KEY `idx_subtarefas_id_relatorio` (`id_relatorio`),
  ADD KEY `idx_subtarefas_atividade` (`id_atividade`),
  ADD KEY `idx_subtarefas_pagamento` (`id_pagamento`);

--
-- Índices de tabela `atividades_subtarefas_historico`
--
ALTER TABLE `atividades_subtarefas_historico`
  ADD PRIMARY KEY (`id_historico`),
  ADD KEY `idx_hist_subtarefa` (`id_subtarefa`),
  ADD KEY `idx_hist_user_data` (`user_id_alvo`,`criado_em`),
  ADD KEY `fk_hist_user_executor` (`user_id_executor`);

--
-- Índices de tabela `atividades_usuarios`
--
ALTER TABLE `atividades_usuarios`
  ADD PRIMARY KEY (`id_vinculo`),
  ADD UNIQUE KEY `uq_atividade_usuario` (`id_atividade`,`id_usuario`),
  ADD KEY `idx_vinculos_usuario` (`id_usuario`);

--
-- Índices de tabela `cronometro_apps_intervalos`
--
ALTER TABLE `cronometro_apps_intervalos`
  ADD PRIMARY KEY (`id_intervalo`),
  ADD KEY `idx_sessao_app_inicio` (`id_sessao`,`nome_app`,`inicio_em`),
  ADD KEY `idx_user_inicio` (`user_id`,`inicio_em`),
  ADD KEY `idx_app_inicio` (`nome_app`,`inicio_em`);

--
-- Índices de tabela `cronometro_eventos_status`
--
ALTER TABLE `cronometro_eventos_status`
  ADD PRIMARY KEY (`id_evento`),
  ADD KEY `idx_sessao_data` (`id_sessao`,`ocorrido_em`),
  ADD KEY `idx_user_data` (`user_id`,`ocorrido_em`);

--
-- Índices de tabela `cronometro_finalizacoes`
--
ALTER TABLE `cronometro_finalizacoes`
  ADD PRIMARY KEY (`id_finalizacao`),
  ADD KEY `idx_user_data` (`user_id`,`criado_em`),
  ADD KEY `idx_sessao` (`id_sessao`),
  ADD KEY `idx_atividade` (`id_atividade`);

--
-- Índices de tabela `cronometro_finalizacoes_subtarefas`
--
ALTER TABLE `cronometro_finalizacoes_subtarefas`
  ADD PRIMARY KEY (`id_item`),
  ADD KEY `idx_finalizacao` (`id_finalizacao`),
  ADD KEY `fk_fin_subtarefas_subtarefa` (`id_subtarefa`);

--
-- Índices de tabela `cronometro_foco_janela`
--
ALTER TABLE `cronometro_foco_janela`
  ADD PRIMARY KEY (`id_foco`),
  ADD KEY `idx_sessao_inicio` (`id_sessao`,`inicio_em`),
  ADD KEY `idx_user_inicio` (`user_id`,`inicio_em`),
  ADD KEY `idx_app_inicio` (`nome_app`,`inicio_em`);

--
-- Índices de tabela `cronometro_relatorios`
--
ALTER TABLE `cronometro_relatorios`
  ADD PRIMARY KEY (`id_relatorio`),
  ADD KEY `idx_rel_sessao` (`id_sessao`),
  ADD KEY `idx_rel_user` (`user_id`),
  ADD KEY `idx_rel_atividade` (`id_atividade`);

--
-- Índices de tabela `cronometro_sessoes`
--
ALTER TABLE `cronometro_sessoes`
  ADD PRIMARY KEY (`id_sessao`),
  ADD UNIQUE KEY `uk_token_sessao` (`token_sessao`),
  ADD KEY `idx_user_inicio` (`user_id`,`iniciado_em`);

--
-- Índices de tabela `declaracoes_dia_itens`
--
ALTER TABLE `declaracoes_dia_itens`
  ADD PRIMARY KEY (`id_item`),
  ADD KEY `idx_user_data` (`user_id`,`referencia_data`),
  ADD KEY `idx_atividade` (`id_atividade`),
  ADD KEY `idx_subtarefa` (`id_subtarefa`);

--
-- Índices de tabela `Pagamentos`
--
ALTER TABLE `Pagamentos`
  ADD PRIMARY KEY (`id_pagamento`),
  ADD KEY `idx_pagamentos_usuario_data` (`id_usuario`,`data_pagamento`);

--
-- Índices de tabela `registros_tempo`
--
ALTER TABLE `registros_tempo`
  ADD PRIMARY KEY (`id_registro`),
  ADD KEY `idx_registros_mes` (`referencia_mes`),
  ADD KEY `idx_registros_user_mes` (`user_id`,`referencia_mes`);

--
-- Índices de tabela `usuarios`
--
ALTER TABLE `usuarios`
  ADD PRIMARY KEY (`id_usuario`),
  ADD UNIQUE KEY `uq_usuarios_user_id` (`user_id`),
  ADD KEY `idx_usuarios_status` (`status_conta`);

--
-- Índices de tabela `usuarios_status_atual`
--
ALTER TABLE `usuarios_status_atual`
  ADD PRIMARY KEY (`id_status`),
  ADD UNIQUE KEY `uq_status_user_id` (`user_id`);

--
-- AUTO_INCREMENT para tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `atividades`
--
ALTER TABLE `atividades`
  MODIFY `id_atividade` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de tabela `atividades_subtarefas`
--
ALTER TABLE `atividades_subtarefas`
  MODIFY `id_subtarefa` bigint NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

--
-- AUTO_INCREMENT de tabela `atividades_subtarefas_historico`
--
ALTER TABLE `atividades_subtarefas_historico`
  MODIFY `id_historico` bigint NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=20;

--
-- AUTO_INCREMENT de tabela `atividades_usuarios`
--
ALTER TABLE `atividades_usuarios`
  MODIFY `id_vinculo` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT de tabela `cronometro_apps_intervalos`
--
ALTER TABLE `cronometro_apps_intervalos`
  MODIFY `id_intervalo` bigint NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=213;

--
-- AUTO_INCREMENT de tabela `cronometro_eventos_status`
--
ALTER TABLE `cronometro_eventos_status`
  MODIFY `id_evento` bigint NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=223;

--
-- AUTO_INCREMENT de tabela `cronometro_finalizacoes`
--
ALTER TABLE `cronometro_finalizacoes`
  MODIFY `id_finalizacao` bigint NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `cronometro_finalizacoes_subtarefas`
--
ALTER TABLE `cronometro_finalizacoes_subtarefas`
  MODIFY `id_item` bigint NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `cronometro_foco_janela`
--
ALTER TABLE `cronometro_foco_janela`
  MODIFY `id_foco` bigint NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=270;

--
-- AUTO_INCREMENT de tabela `cronometro_relatorios`
--
ALTER TABLE `cronometro_relatorios`
  MODIFY `id_relatorio` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=46;

--
-- AUTO_INCREMENT de tabela `cronometro_sessoes`
--
ALTER TABLE `cronometro_sessoes`
  MODIFY `id_sessao` bigint NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=56;

--
-- AUTO_INCREMENT de tabela `declaracoes_dia_itens`
--
ALTER TABLE `declaracoes_dia_itens`
  MODIFY `id_item` bigint NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=18;

--
-- AUTO_INCREMENT de tabela `Pagamentos`
--
ALTER TABLE `Pagamentos`
  MODIFY `id_pagamento` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de tabela `registros_tempo`
--
ALTER TABLE `registros_tempo`
  MODIFY `id_registro` bigint NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=19;

--
-- AUTO_INCREMENT de tabela `usuarios`
--
ALTER TABLE `usuarios`
  MODIFY `id_usuario` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de tabela `usuarios_status_atual`
--
ALTER TABLE `usuarios_status_atual`
  MODIFY `id_status` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=85;

--
-- Restrições para tabelas despejadas
--

--
-- Restrições para tabelas `atividades_subtarefas`
--
ALTER TABLE `atividades_subtarefas`
  ADD CONSTRAINT `fk_subtarefas_atividade` FOREIGN KEY (`id_atividade`) REFERENCES `atividades` (`id_atividade`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_subtarefas_pagamento` FOREIGN KEY (`id_pagamento`) REFERENCES `Pagamentos` (`id_pagamento`) ON DELETE SET NULL ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_subtarefas_relatorio` FOREIGN KEY (`id_relatorio`) REFERENCES `cronometro_relatorios` (`id_relatorio`) ON DELETE SET NULL ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_subtarefas_sessao` FOREIGN KEY (`id_sessao`) REFERENCES `cronometro_sessoes` (`id_sessao`) ON DELETE SET NULL ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_subtarefas_usuario` FOREIGN KEY (`user_id`) REFERENCES `usuarios` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Restrições para tabelas `atividades_subtarefas_historico`
--
ALTER TABLE `atividades_subtarefas_historico`
  ADD CONSTRAINT `fk_hist_subtarefa` FOREIGN KEY (`id_subtarefa`) REFERENCES `atividades_subtarefas` (`id_subtarefa`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_hist_user_alvo` FOREIGN KEY (`user_id_alvo`) REFERENCES `usuarios` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_hist_user_executor` FOREIGN KEY (`user_id_executor`) REFERENCES `usuarios` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Restrições para tabelas `atividades_usuarios`
--
ALTER TABLE `atividades_usuarios`
  ADD CONSTRAINT `fk_vinculo_atividade` FOREIGN KEY (`id_atividade`) REFERENCES `atividades` (`id_atividade`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_vinculo_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuario`) ON DELETE CASCADE;

--
-- Restrições para tabelas `cronometro_apps_intervalos`
--
ALTER TABLE `cronometro_apps_intervalos`
  ADD CONSTRAINT `fk_apps_sessao` FOREIGN KEY (`id_sessao`) REFERENCES `cronometro_sessoes` (`id_sessao`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_apps_usuario` FOREIGN KEY (`user_id`) REFERENCES `usuarios` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Restrições para tabelas `cronometro_eventos_status`
--
ALTER TABLE `cronometro_eventos_status`
  ADD CONSTRAINT `fk_eventos_sessao` FOREIGN KEY (`id_sessao`) REFERENCES `cronometro_sessoes` (`id_sessao`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_eventos_usuario` FOREIGN KEY (`user_id`) REFERENCES `usuarios` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Restrições para tabelas `cronometro_finalizacoes`
--
ALTER TABLE `cronometro_finalizacoes`
  ADD CONSTRAINT `fk_finalizacoes_atividade` FOREIGN KEY (`id_atividade`) REFERENCES `atividades` (`id_atividade`) ON DELETE RESTRICT ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_finalizacoes_sessao` FOREIGN KEY (`id_sessao`) REFERENCES `cronometro_sessoes` (`id_sessao`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_finalizacoes_usuario` FOREIGN KEY (`user_id`) REFERENCES `usuarios` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Restrições para tabelas `cronometro_finalizacoes_subtarefas`
--
ALTER TABLE `cronometro_finalizacoes_subtarefas`
  ADD CONSTRAINT `fk_fin_subtarefas_finalizacao` FOREIGN KEY (`id_finalizacao`) REFERENCES `cronometro_finalizacoes` (`id_finalizacao`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_fin_subtarefas_subtarefa` FOREIGN KEY (`id_subtarefa`) REFERENCES `atividades_subtarefas` (`id_subtarefa`) ON DELETE RESTRICT ON UPDATE CASCADE;

--
-- Restrições para tabelas `cronometro_foco_janela`
--
ALTER TABLE `cronometro_foco_janela`
  ADD CONSTRAINT `fk_foco_sessao` FOREIGN KEY (`id_sessao`) REFERENCES `cronometro_sessoes` (`id_sessao`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_foco_usuario` FOREIGN KEY (`user_id`) REFERENCES `usuarios` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Restrições para tabelas `cronometro_sessoes`
--
ALTER TABLE `cronometro_sessoes`
  ADD CONSTRAINT `fk_cronometro_sessoes_usuario` FOREIGN KEY (`user_id`) REFERENCES `usuarios` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Restrições para tabelas `declaracoes_dia_itens`
--
ALTER TABLE `declaracoes_dia_itens`
  ADD CONSTRAINT `fk_decl_atividade` FOREIGN KEY (`id_atividade`) REFERENCES `atividades` (`id_atividade`) ON DELETE RESTRICT ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_decl_user` FOREIGN KEY (`user_id`) REFERENCES `usuarios` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Restrições para tabelas `Pagamentos`
--
ALTER TABLE `Pagamentos`
  ADD CONSTRAINT `fk_pagamentos_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuario`) ON DELETE CASCADE;

--
-- Restrições para tabelas `registros_tempo`
--
ALTER TABLE `registros_tempo`
  ADD CONSTRAINT `fk_registros_usuario` FOREIGN KEY (`user_id`) REFERENCES `usuarios` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Restrições para tabelas `usuarios_status_atual`
--
ALTER TABLE `usuarios_status_atual`
  ADD CONSTRAINT `fk_status_usuario` FOREIGN KEY (`user_id`) REFERENCES `usuarios` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
