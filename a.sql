/* ============================================================================
   PROJETO: Royal Drip (E-commerce de Moda / Streetwear)
   INTEGRANTES: [Isabelly Vitoria, Ana Beatriz Cristofolette, Leticia Cristina, Thiago Barbosa, Arthur de Jesus]
   DATA: 09/10/2026
   ----------------------------------------------------------------------------
   Usuários de teste (senhas já com hash do Werkzeug, o mesmo usado no Flask):
     lucas@email.com  / 123456     (Cliente)
     admin@email.com  / admin123   (Administrador)
   ============================================================================ */

-- ATENÇÃO: apaga o banco antigo e recria tudo do zero (evita conflito com as
-- tabelas da versão anterior: clientes, produtos com tamanho/cor, senhas inválidas...).
-- Se já tiver usuários cadastrados pelo site que quer manter, comente esta linha.
DROP DATABASE IF EXISTS ROYAL_DRIP_SQL;

CREATE DATABASE IF NOT EXISTS ROYAL_DRIP_SQL
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE ROYAL_DRIP_SQL;

-- ----------------------------------------------------------------------------
-- 1. ESTRUTURA
-- ----------------------------------------------------------------------------

-- Perfis de acesso (Cliente / Administrador)
CREATE TABLE IF NOT EXISTS perfis (
    id_perfil INT AUTO_INCREMENT PRIMARY KEY,
    nome_perfil VARCHAR(30) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- Os perfis precisam existir ANTES de qualquer usuário (chave estrangeira)
INSERT INTO perfis (id_perfil, nome_perfil) VALUES
(1, 'Cliente'),
(2, 'Administrador')
ON DUPLICATE KEY UPDATE nome_perfil = VALUES(nome_perfil);

-- Usuários (única tabela de login/cadastro; substitui "clientes")
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_perfil INT NOT NULL DEFAULT 1,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,          -- hash gerado por generate_password_hash
    telefone VARCHAR(20),
    cep CHAR(8),
    cidade VARCHAR(50),
    estado CHAR(2),
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_usuarios_perfis FOREIGN KEY (id_perfil) REFERENCES perfis(id_perfil)
) ENGINE=InnoDB;

-- Categorias
CREATE TABLE IF NOT EXISTS categorias (
    id_categoria INT AUTO_INCREMENT PRIMARY KEY,
    nome_categoria VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- Produtos (os mesmos 42 itens exibidos no site)
-- O tamanho NÃO fica aqui: um produto tem vários tamanhos, que são escolhidos
-- no carrinho / pedido.
CREATE TABLE IF NOT EXISTS produtos (
    id_produto INT AUTO_INCREMENT PRIMARY KEY,
    id_categoria INT NOT NULL,
    nome_produto VARCHAR(100) NOT NULL,
    descricao TEXT,
    preco DECIMAL(10,2) NOT NULL,
    estoque INT NOT NULL DEFAULT 0,
    imagem_url VARCHAR(255) DEFAULT 'default.jpg',
    ativo BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_produtos_categorias FOREIGN KEY (id_categoria) REFERENCES categorias(id_categoria)
) ENGINE=InnoDB;

-- Carrinho (um carrinho por usuário)
CREATE TABLE IF NOT EXISTS carrinho (
    id_carrinho INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    id_produto INT NOT NULL,
    tamanho VARCHAR(10) NOT NULL,
    quantidade INT NOT NULL DEFAULT 1,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_carrinho_usuarios FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_carrinho_produtos FOREIGN KEY (id_produto) REFERENCES produtos(id_produto),
    -- mesmo produto + mesmo tamanho = mesma linha (soma a quantidade)
    CONSTRAINT uq_carrinho_item UNIQUE (id_usuario, id_produto, tamanho)
) ENGINE=InnoDB;

-- Pedidos
CREATE TABLE IF NOT EXISTS pedidos (
    id_pedido INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    data_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,
    valor_total DECIMAL(10,2) NOT NULL,
    status_pedido VARCHAR(30) DEFAULT 'Finalizado',
    CONSTRAINT fk_pedidos_usuarios FOREIGN KEY (id_usuario) REFERENCES usuarios(id)
) ENGINE=InnoDB;

-- Itens do pedido
CREATE TABLE IF NOT EXISTS itens_pedido (
    id_item INT AUTO_INCREMENT PRIMARY KEY,
    id_pedido INT NOT NULL,
    id_produto INT NOT NULL,
    tamanho VARCHAR(10) NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_itens_pedidos FOREIGN KEY (id_pedido) REFERENCES pedidos(id_pedido),
    CONSTRAINT fk_itens_produtos FOREIGN KEY (id_produto) REFERENCES produtos(id_produto),
    CONSTRAINT uq_item_pedido UNIQUE (id_pedido, id_produto, tamanho)
) ENGINE=InnoDB;


-- ----------------------------------------------------------------------------
-- 2. DADOS DE TESTE
-- ----------------------------------------------------------------------------

-- Categorias
INSERT INTO categorias (id_categoria, nome_categoria) VALUES
(1, 'Camisetas'),
(2, 'Conjuntos'),
(3, 'Calças'),
(4, 'Gorros'),
(5, 'Cintos')
ON DUPLICATE KEY UPDATE nome_categoria = VALUES(nome_categoria);

-- Usuários (senhas com hash real do Werkzeug)
INSERT INTO usuarios (id, id_perfil, nome, email, senha, telefone, cidade, estado) VALUES
(1, 1, 'Lucas Silva',    'lucas@email.com',    'pbkdf2:sha256:1000000$mqA4pKyZJP1B6mRS$79ac46cec917c58cdb643e15645562bfbc8d80067d796507c86a5848c9f064f1', '11999990001', 'São Paulo',      'SP'),
(2, 1, 'Mariana Costa',  'mariana@email.com',  'pbkdf2:sha256:1000000$mqA4pKyZJP1B6mRS$79ac46cec917c58cdb643e15645562bfbc8d80067d796507c86a5848c9f064f1', '21999990002', 'Rio de Janeiro', 'RJ'),
(3, 1, 'Felipe Andrade', 'felipe@email.com',  'pbkdf2:sha256:1000000$mqA4pKyZJP1B6mRS$79ac46cec917c58cdb643e15645562bfbc8d80067d796507c86a5848c9f064f1', '41999990003', 'Curitiba',       'PR'),
(4, 1, 'Camila Rocha',   'camila@email.com',   'pbkdf2:sha256:1000000$mqA4pKyZJP1B6mRS$79ac46cec917c58cdb643e15645562bfbc8d80067d796507c86a5848c9f064f1', '31999990004', 'Belo Horizonte', 'MG'),
(5, 2, 'Administrador',  'admin@email.com',    'pbkdf2:sha256:1000000$BhqbB0S7ZbvI9OBE$27dbba1897d2df8f36ddfa48f0cef4fdbaf2f43722d1ceb4d14e5c945cdb5d41', '11999990005', 'São Paulo',      'SP')
ON DUPLICATE KEY UPDATE
    nome = VALUES(nome),
    id_perfil = VALUES(id_perfil),
    senha = VALUES(senha);   -- redefine a senha dos usuários de teste

-- Produtos: mesmos ids, títulos e preços do dicionário PRODUTOS (produtos.py)
INSERT INTO produtos (id_produto, id_categoria, nome_produto, descricao, preco, estoque, imagem_url) VALUES
(1, 1, 'Camisa Boxy Dark Angel Drop 01', 'Modelagem ampla com corte streetwear moderno, algodão encorpado e acabamento premium.', 129.90, 45, 'imagens/camisas/camisa 1.webp'),
(2, 1, 'Camisa Boxy Black Bite Drop 02', 'Corte oversized com visual urbano, estampa marcante e tecido confortável.', 139.90, 40, 'imagens/camisas/camisa 2.webp'),
(3, 1, 'Camisa Boxy Light Bite Drop 03', 'Edição leve com visual clean, caimento amplo e acabamento premium.', 149.90, 35, 'imagens/camisas/camisa 3.webp'),
(4, 1, 'Camisa Boxy Brasilian Once', 'Camisa Boxy Brasilian Once com estampa exclusiva e caimento oversized.', 139.90, 40, 'imagens/camisas/camisa boxy brasilian once.webp'),
(5, 1, 'Camisa Boxy Come In', 'Camisa Boxy Come In com estampa urbana e tecido encorpado.', 139.90, 40, 'imagens/camisas/camisa boxy come in.webp'),
(6, 1, 'Camisa Boxy Good Plan', 'Camisa Boxy Good Plan com caimento streetwear amplo.', 139.90, 40, 'imagens/camisas/camisa boxy good plan.webp'),
(7, 2, 'Conjunto Cinza Street Drop 01', 'Moletom pesado com capuz e calça em modelo confortável.', 289.90, 20, 'imagens/blusas_Conjuntos/conjunto moletom cinza.webp'),
(8, 2, 'Conjunto UK Drop 02', 'Visual urbano e com textura premium.', 299.90, 20, 'imagens/blusas_Conjuntos/USA.webp'),
(9, 2, 'Conjunto Branco Street Drop 03', 'Estilo minimalista com acabamento refinado e tecido macio.', 319.90, 18, 'imagens/blusas_Conjuntos/conjunto branco copy.webp'),
(10, 2, 'Conjunto Blue Street Drop 04', 'Conjunto em tom azul com visual esportivo e premium.', 329.90, 15, 'imagens/blusas_Conjuntos/conj2.webp'),
(11, 2, 'Conjunto Camuflado Street Drop 05', 'Estampa camuflada com visual robusto e capuz reforçado.', 339.90, 15, 'imagens/blusas_Conjuntos/conj3.webp'),
(12, 2, 'Conjunto Cimento Street Drop 06', 'Tom cimento com acabamento refinado e caimento largo.', 349.90, 12, 'imagens/blusas_Conjuntos/conj4.webp'),
(13, 3, 'Calça de Moletom Lettering Drop 07', 'Calça de moletom com conforto premium e ajuste elástico.', 239.90, 25, 'imagens/calcas/Calça Moletom.webp'),
(14, 3, 'Calça de Moletom Branca Drop 08', 'Visual clean e contemporâneo com tecido confortável.', 247.90, 22, 'imagens/calcas/calça branca.webp'),
(15, 3, 'Calça de Moletom Azul Drop 09', 'Corte esportivo versátil e toque macio.', 249.90, 22, 'imagens/calcas/calça azul.webp'),
(16, 3, 'Calça Jeans Baggy Hard', 'Modelagem baggy com jeans encorpado de alta gramatura.', 269.90, 20, 'imagens/calcas/calça jeans hard 2.webp'),
(17, 3, 'Calça Jeans Baggy Worn Out', 'Visual vintage desgastado com estampa streetwear marcante.', 279.90, 20, 'imagens/calcas/calça jeans hard.webp'),
(18, 3, 'Calça Regular Bless', 'Corte reto contemporâneo com apliques em alto relevo.', 259.90, 20, 'imagens/calcas/calça regular bless.webp'),
(19, 3, 'Calça Jeans Sant', 'Estampa sacra oversized impressa em jeans escuro.', 289.90, 20, 'imagens/calcas/calça jeans sant.webp'),
(20, 3, 'Calça Jeans Barrel', 'Modelagem Barrel curvada nas pernas com tom jeans escuro.', 249.90, 20, 'imagens/calcas/calça jeans barrel.webp'),
(21, 3, 'Calça Baggy Nation', 'Corte oversized com tipografia Nation gravada ao longo da perna.', 299.90, 20, 'imagens/calcas/calça baggy nation.webp'),
(22, 3, 'Calça Jeans Baggy Camuflada', 'Estampa camuflada militar em sarja encorpada com modelagem bem larga.', 269.90, 20, 'imagens/calcas/calça baggy camuflada.webp'),
(23, 4, 'Gorro Oncinha Y2K', 'Gorro em tricô macio com estampa animal print Y2K.', 79.90, 50, 'imagens/gorros/gorro oncinha y2k.webp'),
(24, 4, 'Gorro Pré Cort', 'Gorro em malha encorpada preta com bordado frontal amplo.', 89.90, 50, 'imagens/gorros/gorro pré cort.webp'),
(25, 4, 'Gorro Y2K Black', 'Gorro preto minimalista estilo Y2K.', 79.90, 50, 'imagens/gorros/gorro y2k black.webp'),
(26, 4, 'Gorro Y2K White', 'Edição branca em lã macia com estampa frontal estilo graffiti.', 79.90, 50, 'imagens/gorros/gorro y2k white.webp'),
(27, 4, 'Gorro White Red', 'Gorro com estampa em contraste vermelho e branco.', 84.90, 50, 'imagens/gorros/gorro white red.webp'),
(28, 5, 'Cinto Blue Star', 'Cinto cravejado com pedras azuis e fivela prateada em formato de estrela Y2K.', 119.90, 35, 'imagens/cintos/blue star.webp'),
(29, 5, 'Cinto Cravejado de Caveira', 'Cinto preto em couro sintético premium com pedras brilhantes e fivela de caveira pirata.', 129.90, 35, 'imagens/cintos/cinto caveira.webp'),
(30, 5, 'Cinto Fly Heart', 'Cinto em estilo punk/streetwear com fivela em formato de coração alado metálico.', 119.90, 35, 'imagens/cintos/fly heart.webp'),
(31, 5, 'Cinto Purple Cup', 'Cinto roxo cravejado com fivela personalizada em liga metálica de alta resistência.', 124.90, 35, 'imagens/cintos/purple cup.webp'),
(32, 5, 'Red Die', 'Cinto vermelho streetwear com detalhes metálicos e fivela marcante.', 119.90, 35, 'imagens/cintos/red die.webp'),
(33, 5, 'Stelar White', 'Cinto branco com fivelas e tachas metálicas em formato de estrela.', 119.90, 35, 'imagens/cintos/stelar white.webp'),
(34, 5, 'Cinto Camuflado', 'Cinto camuflado com a fivela personalizada com escritas douradas.', 119.90, 35, 'imagens/cintos/cinto camuflado.webp'),
(35, 5, 'Cinto Swag Branco', 'Cinto branco com fivelas e tachas metálicas em formato de ST.', 119.90, 35, 'imagens/cintos/cinto swag branco.webp'),
(36, 5, 'Cinto Swag Preto', 'Cinto preto com fivelas e tachas metálicas em formato de ST.', 119.90, 35, 'imagens/cintos/cinto swag preto.webp'),
(37, 5, 'Cinto Lunar BL', 'Cinto preto com fivelas e tachas metálicas em formato de lua.', 119.90, 35, 'imagens/cintos/cinto lunar bl.webp'),
(38, 5, 'Cinto Marrom Star', 'Cinto marrom com fivelas e tachas metálicas em formato de estrela.', 119.90, 35, 'imagens/cintos/cinto marrom star.webp'),
(39, 5, 'Cinto Couro Cowboy', 'Cinto de couro cowboy com fivelas e tachas metálicas.', 119.90, 35, 'imagens/cintos/cinto couro cowboy.webp'),
(40, 1, 'Camisa Boxy Sant BR', 'Camisa Boxy Sant BR com estampa exclusiva e caimento oversized.', 139.90, 40, 'imagens/camisas/camisa box sant br.webp'),
(41, 1, 'Camisa Boxy Red Los Angeles', 'Camisa Boxy Red Los Angeles com visual urbano e tecido encorpado.', 139.90, 40, 'imagens/camisas/camisa box red los angeles.webp'),
(42, 1, 'Camisa Boxy Jersey 22', 'Camisa Boxy Jersey 22 com estilo esportivo e caimento streetwear amplo.', 139.90, 40, 'imagens/camisas/camisa box jersey 22.webp')
ON DUPLICATE KEY UPDATE
    id_categoria = VALUES(id_categoria),
    nome_produto = VALUES(nome_produto),
    descricao    = VALUES(descricao),
    preco        = VALUES(preco),
    imagem_url   = VALUES(imagem_url);

-- Pedidos (valor_total = soma dos itens abaixo)
INSERT IGNORE INTO pedidos (id_pedido, id_usuario, data_pedido, valor_total, status_pedido) VALUES
(1001, 1, '2026-10-01 10:30:00', 269.80, 'Finalizado'),   -- 129.90 + 139.90
(1002, 2, '2026-10-02 14:15:00', 289.90, 'Finalizado'),   -- 289.90
(1003, 1, '2026-10-04 18:00:00', 569.80, 'Finalizado'),   -- 239.90 + 329.90
(1004, 3, '2026-10-05 11:20:00', 149.90, 'Finalizado');   -- 149.90

-- Itens dos pedidos
INSERT IGNORE INTO itens_pedido (id_pedido, id_produto, tamanho, quantidade, preco_unitario) VALUES
(1001, 1,  'G',  1, 129.90),
(1001, 2,  'M',  1, 139.90),
(1002, 7,  'GG', 1, 289.90),   -- Conjunto Cinza Street Drop 01
(1003, 13, 'G',  1, 239.90),   -- Calça de Moletom Lettering Drop 07
(1003, 10, 'M',  1, 329.90),   -- Conjunto Blue Street Drop 04
(1004, 3,  'P',  1, 149.90);


-- ============================================================================
-- 3. RELATÓRIOS E TAREFAS ACADÊMICAS
-- ============================================================================

-- TAREFA 1: COUNT
SELECT COUNT(id_produto) AS quantidade_itens_catalogo FROM produtos;

-- TAREFA 2: SUM
SELECT SUM(preco * estoque) AS valor_total_estoque_reais FROM produtos;

-- TAREFA 3: AVG
SELECT AVG(preco) AS preco_medio_pecas_reais FROM produtos;

-- TAREFA 4: GROUP BY
SELECT id_categoria, COUNT(id_produto) AS total_produtos, AVG(preco) AS preco_medio_categoria_reais
FROM produtos
GROUP BY id_categoria;

-- TAREFA 5: INNER JOIN
SELECT c.nome_categoria, p.nome_produto, ip.quantidade, ip.preco_unitario AS preco_unitario_reais
FROM produtos p
INNER JOIN categorias c ON p.id_categoria = c.id_categoria
INNER JOIN itens_pedido ip ON p.id_produto = ip.id_produto;

-- DESAFIO: INNER JOIN + GROUP BY
SELECT c.nome_categoria,
       SUM(ip.quantidade) AS total_pecas_vendidas,
       SUM(ip.quantidade * ip.preco_unitario) AS faturamento_categoria_reais
FROM categorias c
INNER JOIN produtos p ON c.id_categoria = p.id_categoria
INNER JOIN itens_pedido ip ON p.id_produto = ip.id_produto
GROUP BY c.id_categoria, c.nome_categoria;


-- ============================================================================
-- 4. CONSULTAS ADICIONAIS (COUNT, SUM, AVG, GROUP BY, INNER JOIN)
-- ============================================================================

-- CONSULTA 1: COUNT + INNER JOIN + GROUP BY
-- Quantidade de pedidos por cliente
SELECT u.nome AS cliente,
       COUNT(p.id_pedido) AS total_pedidos
FROM usuarios u
INNER JOIN pedidos p ON u.id = p.id_usuario
GROUP BY u.id, u.nome
ORDER BY total_pedidos DESC, u.nome;

-- CONSULTA 2: SUM + INNER JOIN + GROUP BY
-- Peças vendidas e faturamento por categoria
SELECT c.nome_categoria AS categoria,
       SUM(ip.quantidade) AS pecas_vendidas,
       SUM(ip.quantidade * ip.preco_unitario) AS faturamento_reais
FROM categorias c
INNER JOIN produtos p      ON c.id_categoria = p.id_categoria
INNER JOIN itens_pedido ip ON p.id_produto = ip.id_produto
GROUP BY c.id_categoria, c.nome_categoria
ORDER BY faturamento_reais DESC;

-- CONSULTA 3: AVG + INNER JOIN + GROUP BY
-- Ticket médio (valor médio dos pedidos) por cliente
SELECT u.nome AS cliente,
       ROUND(AVG(p.valor_total), 2) AS ticket_medio_reais
FROM usuarios u
INNER JOIN pedidos p ON u.id = p.id_usuario
GROUP BY u.id, u.nome
ORDER BY ticket_medio_reais DESC;

-- CONSULTA 4: COUNT + AVG + SUM + GROUP BY
-- Resumo do catálogo por categoria (qtd. de produtos, preço médio e estoque)
SELECT c.nome_categoria AS categoria,
       COUNT(p.id_produto) AS qtd_produtos,
       ROUND(AVG(p.preco), 2) AS preco_medio_reais,
       SUM(p.estoque) AS pecas_em_estoque
FROM categorias c
INNER JOIN produtos p ON c.id_categoria = p.id_categoria
GROUP BY c.id_categoria, c.nome_categoria
ORDER BY c.nome_categoria;

-- CONSULTA 5: SUM + COUNT + INNER JOIN + GROUP BY
-- Pedidos e faturamento por estado do cliente
SELECT u.estado,
       COUNT(p.id_pedido) AS total_pedidos,
       SUM(p.valor_total) AS faturamento_reais
FROM usuarios u
INNER JOIN pedidos p ON u.id = p.id_usuario
GROUP BY u.estado
ORDER BY faturamento_reais DESC;

-- CONSULTA DA TELA DE PEDIDOS DOS CLIENTES
SELECT 
    p.id_pedido,
    p.data_pedido,
    p.valor_total,
    p.status_pedido AS status,
    u.nome AS cliente_nome,
    u.email AS cliente_email
FROM pedidos p
INNER JOIN usuarios u ON p.id_usuario = u.id
ORDER BY p.data_pedido DESC;

-- VERIFICAR A ESTRUTURA DA TABELA PEDIDOS
DESCRIBE pedidos;



-- =====================================================================
-- GRUPO: [Isabelly Vitoria, Ana Beatriz Cristofolette, Leticia Cristina, Thiago Barbosa, Arthur de Jesus]
-- PROJETO: Royal Drip (E-commerce de Moda / Streetwear)
-- 
-- ETAPA 1: Escolha a relação entre tabelas
-- - Tabela Principal: usuarios (armazena os dados cadastrais dos clientes e admin)
-- - Tabela Relacionada: pedidos (armazena as compras realizadas no site)
-- - Chave Primária: usuarios.id
-- - Chave Estrangeira: pedidos.id_usuario
-- - Pergunta que o sistema quer responder: "Quais usuários cadastrados ainda não realizaram 
--   nenhum pedido e podem receber e-mails de remarketing ou cupom de boas-vindas?"
-- - Registro sem correspondente: O usuário "Camila Rocha" (id 4) ou o "Administrador" (id 5), 
--   pois foram cadastrados mas ainda não efetuaram nenhuma compra.
-- =====================================================================

-- 1. INNER JOIN: Registros que possuem correspondência nas duas tabelas
SELECT 
    u.id AS usuario_id,
    u.nome AS usuario_nome,
    p.id_pedido,
    p.data_pedido
FROM usuarios u
INNER JOIN pedidos p ON u.id = p.id_usuario;
-- Comentário: Mantém apenas os usuários que possuem pelo menos um pedido vinculado. 
-- Usuários sem compras (como a Camila e o Admin) e pedidos sem usuário deixam de aparecer.

-- 2. LEFT JOIN: Todos os registros da tabela principal (usuarios)
SELECT 
    u.id AS usuario_id,
    u.nome AS usuario_nome,
    p.id_pedido,
    p.data_pedido
FROM usuarios u
LEFT JOIN pedidos p ON u.id = p.id_usuario;
-- Comentário: Mantém todos os usuários. Se um usuário fez vários pedidos, ele 
-- aparecerá em múltiplas linhas. Se não fez pedidos (caso da Camila e do Admin), 
-- os dados do pedido aparecerão como NULL.

-- 3. RIGHT JOIN: Invertendo a ordem das tabelas
SELECT 
    u.id AS usuario_id,
    u.nome AS usuario_nome,
    p.id_pedido,
    p.data_pedido
FROM pedidos p
RIGHT JOIN usuarios u ON u.id = p.id_usuario;
-- Comentário: Inverte a ordem colocando a tabela `pedidos` à esquerda e `usuarios` 
-- à direita. O uso do RIGHT JOIN garante que todos os usuários apareçam, mantendo 
-- o mesmo resultado prático da consulta com LEFT JOIN.

-- 4. LEFT JOIN + IS NULL: Somente registros da tabela principal sem vínculo
SELECT 
    u.id AS usuario_id,
    u.nome AS usuario_nome,
    u.email
FROM usuarios u
LEFT JOIN pedidos p ON u.id = p.id_usuario
WHERE p.id_pedido IS NULL;
-- Comentário: Filtra o resultado do LEFT JOIN para exibir exclusivamente os 
-- usuários cadastrados que não possuem nenhuma correspondência na tabela de pedidos.

-- =====================================================================
-- ETAPA 4: Relacionamento com o projeto
-- - Onde essa informação seria útil: No painel administrativo da Royal Drip 
--   para identificar novos cadastros inativos e disparar campanhas de e-mail marketing.
-- - O que o usuário entenderia: Que o cliente criou uma conta na loja, mas 
--   ainda não finalizou nenhuma compra de streetwear.
-- - Qual consulta usar: A consulta 4 (LEFT JOIN com IS NULL), pois isola perfeitamente 
--   os clientes sem histórico de compras para ações direcionadas.
-- =====================================================================