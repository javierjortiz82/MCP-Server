#!/usr/bin/env python3
"""Script de verificación para la configuración del bot de Telegram.

Este script verifica que:
1. Todos los servicios externos están disponibles (ASR, OCR, Sentiment)
2. Las dependencias de Python están instaladas
3. Las variables de entorno están configuradas
4. Los archivos de código son válidos

Usage:
    python scripts/verify_telegram_setup.py
"""

import sys
import os
from pathlib import Path

# Colores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_success(msg: str):
    """Print mensaje de éxito."""
    print(f"{GREEN}✅ {msg}{RESET}")


def print_error(msg: str):
    """Print mensaje de error."""
    print(f"{RED}❌ {msg}{RESET}")


def print_warning(msg: str):
    """Print mensaje de advertencia."""
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def print_header(msg: str):
    """Print encabezado."""
    print(f"\n{BOLD}{msg}{RESET}")
    print("=" * 60)


def check_python_version():
    """Verifica versión de Python >= 3.10."""
    print_header("1. Verificando versión de Python")

    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor} - Se requiere Python >= 3.10")
        return False


def check_dependencies():
    """Verifica que las dependencias estén instaladas."""
    print_header("2. Verificando dependencias de Python")

    required_packages = [
        ("telegram", "python-telegram-bot"),
        ("httpx", "httpx"),
        ("dotenv", "python-dotenv (opcional)")
    ]

    all_ok = True
    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
            print_success(f"{package_name}")
        except ImportError:
            if "opcional" in package_name:
                print_warning(f"{package_name} - No instalado (opcional)")
            else:
                print_error(f"{package_name} - No instalado")
                all_ok = False

    return all_ok


def check_services():
    """Verifica que los servicios externos estén disponibles."""
    print_header("3. Verificando servicios externos")

    try:
        import httpx
    except ImportError:
        print_error("httpx no instalado - No se pueden verificar servicios")
        return False

    services = [
        ("Voice-ASR", "http://localhost:8085/health"),
        ("Sentiment", "http://localhost:8003/health"),
        ("OCR-Multilang", "http://localhost:8004/health")
    ]

    all_ok = True
    for service_name, url in services:
        try:
            import asyncio

            async def check_health():
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(url)
                    return response.status_code == 200

            is_healthy = asyncio.run(check_health())

            if is_healthy:
                print_success(f"{service_name} ({url})")
            else:
                print_error(f"{service_name} ({url}) - No responde correctamente")
                all_ok = False
        except Exception as e:
            print_error(f"{service_name} ({url}) - Error: {str(e)}")
            all_ok = False

    return all_ok


def check_environment():
    """Verifica variables de entorno."""
    print_header("4. Verificando variables de entorno")

    # Intentar cargar .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print_success("Archivo .env cargado")
    except ImportError:
        print_warning("python-dotenv no instalado - Usando solo variables de entorno del sistema")
    except Exception:
        print_warning("No se encontró archivo .env")

    # Verificar TELEGRAM_BOT_TOKEN
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token:
        print_success(f"TELEGRAM_BOT_TOKEN configurado ({token[:10]}...{token[-4:]})")
    else:
        print_error("TELEGRAM_BOT_TOKEN no configurado")
        print(f"\n   {YELLOW}Configura con:{RESET}")
        print(f"   export TELEGRAM_BOT_TOKEN='tu_token_aqui'")
        print(f"   {YELLOW}O crea archivo .env:{RESET}")
        print(f"   echo 'TELEGRAM_BOT_TOKEN=tu_token' > .env\n")
        return False

    # Verificar TELEGRAM_SUPPORT_GROUP_ID (opcional)
    support_group = os.getenv("TELEGRAM_SUPPORT_GROUP_ID")
    if support_group:
        print_success(f"TELEGRAM_SUPPORT_GROUP_ID configurado ({support_group})")
    else:
        print_warning("TELEGRAM_SUPPORT_GROUP_ID no configurado (opcional)")
        print(f"   {YELLOW}El escalamiento por urgencia no funcionará sin esto{RESET}\n")

    return True


def check_files():
    """Verifica que los archivos de código existan."""
    print_header("5. Verificando archivos de código")

    project_root = Path(__file__).parent.parent

    required_files = [
        "integrations/clients/__init__.py",
        "integrations/clients/asr_client.py",
        "integrations/clients/ocr_client.py",
        "integrations/clients/sentiment_client.py",
        "integrations/telegram_adapter.py",
        "chat_core/chat_core.py",
        "main_telegram.py"
    ]

    all_ok = True
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print_success(file_path)
        else:
            print_error(f"{file_path} - No encontrado")
            all_ok = False

    return all_ok


def print_next_steps():
    """Imprime los próximos pasos."""
    print_header("✨ Próximos pasos")

    print(f"""
{BOLD}Para ejecutar el bot:{RESET}

1. Asegúrate de que todos los servicios estén corriendo:
   {GREEN}docker ps{RESET}

2. Configura tu token de Telegram:
   {GREEN}export TELEGRAM_BOT_TOKEN='tu_token_aqui'{RESET}

3. (Opcional) Configura grupo de soporte:
   {GREEN}export TELEGRAM_SUPPORT_GROUP_ID='-1001234567890'{RESET}

4. Ejecuta el bot:
   {GREEN}python main_telegram.py{RESET}

{BOLD}Para obtener más ayuda:{RESET}
   Ver: {YELLOW}docs/TELEGRAM_MULTIMEDIA_IMPLEMENTATION.md{RESET}
""")


def main():
    """Ejecuta todas las verificaciones."""
    print(f"\n{BOLD}🔍 Verificación de Configuración del Bot de Telegram{RESET}")
    print(f"{BOLD}================================================{RESET}")

    checks = [
        check_python_version(),
        check_dependencies(),
        check_services(),
        check_environment(),
        check_files()
    ]

    print_header("📊 Resumen")

    passed = sum(checks)
    total = len(checks)

    if passed == total:
        print(f"\n{GREEN}{BOLD}✅ Todas las verificaciones pasaron ({passed}/{total}){RESET}")
        print(f"{GREEN}El bot está listo para ejecutarse{RESET}\n")
        print_next_steps()
        return 0
    else:
        print(f"\n{RED}{BOLD}❌ Algunas verificaciones fallaron ({passed}/{total}){RESET}")
        print(f"{RED}Corrige los errores antes de ejecutar el bot{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
