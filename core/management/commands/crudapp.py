from pathlib import Path
from django.core.management import call_command
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Cria um app com a estrutura padrão do ERP"

    def add_arguments(self, parser):
        parser.add_argument("nome", help="Nome do app")
        parser.add_argument("--plural", help="Nome no plural (ex: Cidades, Informações, Países)", default=None,)

    def substituir(self, texto, nome, plural):
        return (
            texto
            .replace("__APP__", nome.lower()).replace("__APP_MAIUSCULO__", nome.upper()).replace("__MODELO__", nome.capitalize()).replace("__MODELO_MINUSCULO__", nome.lower())
            .replace("__MODELO_PLURAL__", plural).replace("__MODELO_PLURAL_MINUSCULO__", plural.lower()).replace("__MODELO_PLURAL_MAIUSCULO__", plural.upper())
        )

    def copiar_template(self, origem, destino, nome, plural):
        texto = origem.read_text(encoding="utf-8")
        texto = self.substituir(texto, nome, plural)
        destino.write_text(texto, encoding="utf-8")

    def handle(self, *args, **options):
        nome = options["nome"]
        plural = options["plural"] or f"{nome.capitalize()}s"
        # Cria o app
        call_command("startapp", nome)
        base = Path.cwd()
        origem = Path(__file__).resolve().parents[2] / "templates_padrao"
        # Cria pasta dos templates
        templates_destino = base / "templates" / nome
        templates_destino.mkdir(parents=True, exist_ok=True)
        # Templates HTML
        for arquivo in ("add.html", "att.html", "lista.html"):
            self.copiar_template(origem / arquivo, templates_destino / arquivo, nome, plural,)
        # Arquivos Python
        for arquivo in ("models.py", "forms.py", "views.py", "urls.py", "admin.py",):
            self.copiar_template(origem / arquivo, base / nome / arquivo, nome, plural,)
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("========================================"))
        self.stdout.write(self.style.SUCCESS(f" App '{nome}' criado com sucesso!"))
        self.stdout.write(self.style.SUCCESS(f" Templates: templates/{nome}/"))
        self.stdout.write(self.style.SUCCESS("========================================"))