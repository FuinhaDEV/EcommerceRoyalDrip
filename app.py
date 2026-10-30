import logging
import os
import re
import secrets
import threading
import unicodedata
from contextlib import contextmanager
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache, wraps
from pathlib import Path

import mysql.connector
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    render_template_string,
    request,
    session,
    url_for,
)
from mysql.connector import pooling
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

from produtos import PRODUTOS

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("royal_drip")

BASE_DIR = Path(__file__).resolve().parent

# Imagens quase nunca mudam: o navegador pode guardar por bastante tempo.
# CSS/JS ficam com cache curto para você ver as alterações rapidamente.
EXT_IMAGENS_CACHE = (".webp", ".png", ".jpg", ".jpeg", ".jpe", ".jfif", ".gif", ".svg", ".ico")


class RoyalDrip(Flask):
    def get_send_file_max_age(self, name):
        if self.debug:
            return 0
        if name and name.lower().endswith(EXT_IMAGENS_CACHE):
            return 60 * 60 * 24 * 30  # 30 dias
        return 60 * 5  # 5 minutos para css/js


app = RoyalDrip(__name__)


# ----------------------------------------------------------------------------
# CONFIGURAÇÃO
# ----------------------------------------------------------------------------
def carregar_secret_key():
    """Usa SECRET_KEY do ambiente; senão gera uma vez e guarda em .secret_key,
    assim as sessões (login) não se perdem a cada reinício do servidor."""
    chave = os.environ.get("SECRET_KEY")
    if chave:
        return chave
    arquivo = BASE_DIR / ".secret_key"
    try:
        if arquivo.is_file():
            conteudo = arquivo.read_text(encoding="utf-8").strip()
            if conteudo:
                return conteudo
        chave = secrets.token_hex(32)
        arquivo.write_text(chave, encoding="utf-8")
        return chave
    except OSError:
        log.warning("Não foi possível salvar .secret_key; usando chave temporária.")
        return secrets.token_hex(32)


app.secret_key = carregar_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
    TEMPLATES_AUTO_RELOAD=True,
)

EMAIL_REGEX = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
NOME_REGEX = r"[A-Za-zÀ-ÿ\s]{3,100}"


# ----------------------------------------------------------------------------
# BANCO DE DADOS (pool de conexões: reaproveita conexões em vez de abrir uma
# nova a cada requisição, que é um dos maiores gargalos de apps Flask + MySQL)
# ----------------------------------------------------------------------------
_pool = None
_pool_lock = threading.Lock()


def _obter_pool():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = pooling.MySQLConnectionPool(
                    pool_name="royal_drip_pool",
                    pool_size=int(os.environ.get("DB_POOL_SIZE", "8")),
                    pool_reset_session=True,
                    host=os.environ.get("DB_HOST", "localhost"),
                    user=os.environ.get("DB_USER", "root"),
                    password=os.environ.get("DB_PASSWORD", "senai105"),
                    database=os.environ.get("DB_NAME", "ROYAL_DRIP_SQL"),
                    connection_timeout=5,  # nunca deixa a página pendurada
                    charset="utf8mb4",
                )
    return _pool


@contextmanager
def conexao_db():
    """Entrega uma conexão do pool. Em caso de erro faz rollback; ao sair,
    devolve a conexão ao pool (close() no pool não fecha de verdade)."""
    con = _obter_pool().get_connection()
    try:
        yield con
    except Exception:
        try:
            con.rollback()
        except mysql.connector.Error:
            pass
        raise
    finally:
        con.close()


# ----------------------------------------------------------------------------
# IMAGENS: usa .webp quando existir; senão cai para o arquivo original.
# Os resultados ficam em cache: antes, cada <img> da home fazia um os.listdir()
# em toda requisição (39 leituras de disco por carregamento da página).
# ----------------------------------------------------------------------------
EXTENSOES_IMAGEM = (".webp", ".jpeg", ".jpg", ".jpe", ".jfif", ".png")


@lru_cache(maxsize=None)
def _listar_pasta(pasta):
    try:
        return tuple(os.listdir(pasta))
    except OSError:
        return ()


@lru_cache(maxsize=None)
def resolver_imagem(caminho):
    """Recebe 'imagens/cintos/blue star.webp' e devolve o arquivo que realmente
    existe em static/ (mesmo nome com outra extensão ou outra caixa de letras).
    Se nada for encontrado, devolve o caminho original."""
    pasta_rel, _, nome = caminho.rpartition("/")
    pasta = os.path.join(app.static_folder, *pasta_rel.split("/"))
    base = os.path.splitext(nome)[0].lower()
    # aceita grafias alternativas do mesmo arquivo (ex.: cowboy/cawboy)
    bases = {base, base.replace("cowboy", "cawboy"), base.replace("cawboy", "cowboy")}

    candidatos = {}
    for arq in _listar_pasta(pasta):
        raiz, ext = os.path.splitext(arq)
        if raiz.lower() in bases and ext.lower() in EXTENSOES_IMAGEM:
            candidatos[ext.lower()] = arq

    for ext in EXTENSOES_IMAGEM:  # prioridade: webp > jpeg > jpg > png
        if ext in candidatos:
            return f"{pasta_rel}/{candidatos[ext]}"
    return caminho


@app.template_global()
def img_url(caminho):
    return resolver_imagem(caminho)


def _slug(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", texto.lower())


for _p in PRODUTOS.values():
    _p["imagem"] = resolver_imagem(_p["imagem"])
    _p["categoria_slug"] = _slug(_p["categoria"])  # "Calças" -> "calcas"


# ----------------------------------------------------------------------------
# AUXILIARES
# ----------------------------------------------------------------------------
def login_obrigatorio(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return wrapper


def iniciar_sessao(usuario):
    session["usuario_id"] = usuario["id"]
    session["usuario_nome"] = usuario["nome"]
    session["usuario_email"] = usuario["email"]
    session["usuario_perfil"] = usuario.get("id_perfil", 1)


def dinheiro(valor):
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def verificar_imagens():
    """Avisa no log se algum produto aponta para uma imagem que não existe."""
    base = app.static_folder
    faltando = [
        (pid, p["imagem"])
        for pid, p in PRODUTOS.items()
        if not os.path.isfile(os.path.join(base, *p["imagem"].split("/")))
    ]
    usando_original = [
        (pid, p["imagem"])
        for pid, p in PRODUTOS.items()
        if not p["imagem"].lower().endswith(".webp")
    ]
    for pid, caminho in usando_original:
        log.info("Produto %s usando original (sem .webp): static/%s", pid, caminho)
    for pid, caminho in faltando:
        log.warning("IMAGEM NAO ENCONTRADA (produto %s): static/%s", pid, caminho)
    if not faltando:
        log.info("Todas as imagens dos produtos foram encontradas.")


# ----------------------------------------------------------------------------
# TRATAMENTO DE ERROS
# Qualquer exceção não prevista agora é gravada COMPLETA no terminal (com o
# arquivo e a linha) e o usuário vê uma página amigável em vez do "500" seco.
# ----------------------------------------------------------------------------
PAGINA_ERRO = """<!doctype html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ titulo }} | Royal Drip</title>
<style>
body{font-family:system-ui,sans-serif;background:#0b0b0b;color:#fff;display:flex;
align-items:center;justify-content:center;min-height:100vh;margin:0;text-align:center}
a{color:#fff;border:1px solid #fff;padding:10px 22px;border-radius:6px;text-decoration:none}
a:hover{background:#fff;color:#000}
</style></head><body><div><h1>{{ titulo }}</h1><p>{{ mensagem }}</p>
<a href="{{ url_for('index') }}">Voltar para a loja</a></div></body></html>"""


@app.errorhandler(404)
def pagina_nao_encontrada(_erro):
    return (
        render_template_string(
            PAGINA_ERRO,
            titulo="Página não encontrada",
            mensagem="O endereço que você tentou acessar não existe.",
        ),
        404,
    )


@app.errorhandler(Exception)
def erro_inesperado(erro):
    if isinstance(erro, HTTPException):
        return erro
    log.exception("ERRO NÃO TRATADO em %s %s", request.method, request.path)
    return (
        render_template_string(
            PAGINA_ERRO,
            titulo="Algo deu errado",
            mensagem="Tivemos um problema ao carregar esta página. Tente novamente.",
        ),
        500,
    )


# ----------------------------------------------------------------------------
# ROTAS
# ----------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", produtos=list(PRODUTOS.values()))


@app.route("/inicio")
def inicio():
    return render_template("inicio.html")


@app.route("/produto/<int:produto_id>")
def produto(produto_id):
    produto_selecionado = PRODUTOS.get(produto_id)
    if produto_selecionado is None:
        return (
            render_template_string(
                PAGINA_ERRO,
                titulo="Produto não encontrado",
                mensagem="Este produto não existe ou saiu de linha.",
            ),
            404,
        )
    return render_template("produto.html", produto=produto_selecionado)


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefone = request.form.get("telefone", "").strip()
        cep = re.sub(r"\D", "", request.form.get("cep", ""))
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get("confirmarSenha", "")

        erros = []

        if not re.fullmatch(NOME_REGEX, nome):
            erros.append("Nome inválido. Use apenas letras e espaços (mínimo 3).")

        if not re.fullmatch(EMAIL_REGEX, email):
            erros.append("E-mail inválido.")

        telefone_numeros = re.sub(r"\D", "", telefone)
        if len(telefone_numeros) < 10 or len(telefone_numeros) > 11:
            erros.append("Telefone inválido. Deve ter 10 ou 11 dígitos.")

        if len(cep) != 8:
            erros.append("CEP inválido. Deve ter 8 números.")

        if len(senha) < 6:
            erros.append("A senha deve ter no mínimo 6 caracteres.")

        if senha != confirmar_senha:
            erros.append("As senhas não coincidem.")

        if erros:
            return render_template("registro.html", erros=erros)

        senha_hash = generate_password_hash(senha, method="pbkdf2:sha256")

        try:
            with conexao_db() as con:
                cur = con.cursor()
                cur.execute(
                    """
                    INSERT INTO usuarios (nome, email, telefone, cep, senha)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (nome, email, telefone_numeros, cep, senha_hash),
                )
                con.commit()
                cur.close()
        except mysql.connector.IntegrityError:
            return render_template("registro.html", erros=["Este e-mail já está cadastrado."])
        except mysql.connector.Error:
            log.exception("Erro ao cadastrar usuário")
            return render_template(
                "registro.html",
                erros=["Não foi possível concluir o cadastro. Tente novamente."],
            )

        return redirect(url_for("login"))

    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        erros = []

        if not re.fullmatch(EMAIL_REGEX, email):
            erros.append("E-mail inválido.")

        if not senha:
            erros.append("Senha obrigatória.")

        if erros:
            return render_template("login.html", erros=erros)

        try:
            with conexao_db() as con:
                cur = con.cursor(dictionary=True)
                cur.execute(
                    "SELECT id, id_perfil, nome, email, senha FROM usuarios WHERE email = %s",
                    (email,),
                )
                usuario = cur.fetchone()
                cur.close()
        except mysql.connector.Error:
            log.exception("Erro no login")
            return render_template(
                "login.html",
                erros=["Erro ao acessar o sistema. Tente novamente."],
            )

        senha_ok = False
        if usuario:
            try:
                senha_ok = check_password_hash(usuario["senha"], senha)
            except Exception:  # noqa: BLE001
                log.exception("Hash de senha inválido para %s", email)

        if senha_ok:
            session.clear()
            iniciar_sessao(usuario)
            return redirect(url_for("index"))

        return render_template("login.html", erros=["E-mail ou senha incorretos."])

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/carrinho/adicionar", methods=["POST"])
@login_obrigatorio
def adicionar_carrinho():
    produto_id = request.form.get("produto_id", type=int)
    tamanho = request.form.get("tamanho", "")

    if produto_id is None or produto_id not in PRODUTOS:
        flash("Produto inválido.")
        return redirect(url_for("index"))

    if tamanho not in PRODUTOS[produto_id]["tamanhos"]:
        flash("Selecione um tamanho válido.")
        return redirect(url_for("produto", produto_id=produto_id))

    quantidade = request.form.get("quantidade", type=int)
    if quantidade is None or quantidade < 1 or quantidade > 10:
        flash("Quantidade inválida (de 1 a 10).")
        return redirect(url_for("produto", produto_id=produto_id))

    try:
        with conexao_db() as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO carrinho (id_usuario, id_produto, tamanho, quantidade)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE quantidade = LEAST(quantidade + %s, 10)
                """,
                (session["usuario_id"], produto_id, tamanho, quantidade, quantidade),
            )
            con.commit()
            cur.close()
    except mysql.connector.Error:
        log.exception("Erro ao adicionar ao carrinho")
        flash("Não foi possível adicionar ao carrinho. Tente novamente.")
        return redirect(url_for("produto", produto_id=produto_id))

    return redirect(url_for("carrinho"))


@app.route("/carrinho")
@login_obrigatorio
def carrinho():
    linhas = []
    try:
        with conexao_db() as con:
            cur = con.cursor(dictionary=True)
            cur.execute(
                """
                SELECT id_carrinho, id_produto, tamanho, quantidade
                FROM carrinho
                WHERE id_usuario = %s
                ORDER BY criado_em DESC
                """,
                (session["usuario_id"],),
            )
            linhas = cur.fetchall()
            cur.close()
    except mysql.connector.Error:
        log.exception("Erro ao carregar carrinho")
        flash("Não foi possível carregar o carrinho agora.")

    itens = []
    total = Decimal("0.00")
    for linha in linhas:
        p = PRODUTOS.get(linha["id_produto"])
        if p is None:
            continue
        subtotal = dinheiro(p["preco"]) * linha["quantidade"]
        total += subtotal
        itens.append(
            {
                "id_carrinho": linha["id_carrinho"],
                "produto": p,
                "tamanho": linha["tamanho"],
                "quantidade": linha["quantidade"],
                "subtotal": subtotal,
            }
        )

    return render_template("carrinho.html", itens=itens, total=total)


@app.route("/carrinho/remover/<int:id_carrinho>", methods=["POST"])
@login_obrigatorio
def remover_carrinho(id_carrinho):
    try:
        with conexao_db() as con:
            cur = con.cursor()
            cur.execute(
                "DELETE FROM carrinho WHERE id_carrinho = %s AND id_usuario = %s",
                (id_carrinho, session["usuario_id"]),
            )
            con.commit()
            cur.close()
    except mysql.connector.Error:
        log.exception("Erro ao remover item do carrinho")
        flash("Não foi possível remover o item.")

    return redirect(url_for("carrinho"))


@app.route("/carrinho/finalizar", methods=["POST"])
@login_obrigatorio
def finalizar_compra():
    """Transforma o carrinho em pedido: tudo ou nada (transação)."""
    try:
        with conexao_db() as con:
            cur = con.cursor(dictionary=True)
            cur.execute(
                """
                SELECT id_produto, tamanho, quantidade
                FROM carrinho
                WHERE id_usuario = %s
                ORDER BY id_produto, tamanho
                FOR UPDATE
                """,
                (session["usuario_id"],),
            )
            linhas = [l for l in cur.fetchall() if l["id_produto"] in PRODUTOS]

            if not linhas:
                con.rollback()
                flash("Seu carrinho está vazio.")
                return redirect(url_for("carrinho"))

            total = Decimal("0.00")
            for l in linhas:
                preco = dinheiro(PRODUTOS[l["id_produto"]]["preco"])
                l["preco"] = preco
                total += preco * l["quantidade"]

            # baixa de estoque (ordenado por produto para evitar deadlock)
            for l in linhas:
                cur.execute(
                    """
                    UPDATE produtos SET estoque = estoque - %s
                    WHERE id_produto = %s AND estoque >= %s
                    """,
                    (l["quantidade"], l["id_produto"], l["quantidade"]),
                )
                if cur.rowcount == 0:
                    con.rollback()
                    titulo = PRODUTOS[l["id_produto"]]["titulo"]
                    flash(f"Estoque insuficiente para: {titulo}.")
                    return redirect(url_for("carrinho"))

            cur.execute(
                """
                INSERT INTO pedidos (id_usuario, valor_total, status_pedido)
                VALUES (%s, %s, 'Finalizado')
                """,
                (session["usuario_id"], total),
            )
            id_pedido = cur.lastrowid

            cur.executemany(
                """
                INSERT INTO itens_pedido
                    (id_pedido, id_produto, tamanho, quantidade, preco_unitario)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [
                    (id_pedido, l["id_produto"], l["tamanho"], l["quantidade"], l["preco"])
                    for l in linhas
                ],
            )
            cur.execute("DELETE FROM carrinho WHERE id_usuario = %s", (session["usuario_id"],))
            con.commit()
            cur.close()
    except mysql.connector.Error:
        log.exception("Erro ao finalizar compra")
        flash("Não foi possível finalizar a compra. Tente novamente.")
        return redirect(url_for("carrinho"))

    flash(f"Pedido #{id_pedido} realizado com sucesso!")
    return redirect(url_for("listar_pedidos"))


@app.route("/pedidos")
@login_obrigatorio
def listar_pedidos():
    pedidos = []
    erro = None
    try:
        with conexao_db() as con:
            cur = con.cursor(dictionary=True)
            cur.execute(
                """
                SELECT id_pedido, data_pedido, valor_total, status_pedido
                FROM pedidos
                WHERE id_usuario = %s
                ORDER BY data_pedido DESC
                """,
                (session["usuario_id"],),
            )
            pedidos = cur.fetchall()
            cur.close()
    except mysql.connector.Error:
        log.exception("Erro ao listar pedidos")
        erro = "Não foi possível carregar os pedidos. Tente novamente."

    return render_template("pedidos.html", pedidos=pedidos, erro=erro)


if __name__ == "__main__":
    verificar_imagens()
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
