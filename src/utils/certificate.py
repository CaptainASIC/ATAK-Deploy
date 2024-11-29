import os
import subprocess
import asyncio
from typing import Dict
from datetime import datetime

from ..config.settings import get_settings
from ..db.models import User

settings = get_settings()

async def generate_certificate(cert_type: str, name: str, user: User) -> Dict[str, str]:
    """
    Generate a new certificate using ATAK's certificate generation tools.
    
    Args:
        cert_type: Type of certificate (client, server, ca)
        name: Name for the certificate
        user: User requesting the certificate
    
    Returns:
        Dict containing certificate information including file paths
    """
    # Ensure certificate directories exist
    os.makedirs(settings.ATAK_CERT_DIR, exist_ok=True)
    os.makedirs(settings.ATAK_FILES_DIR, exist_ok=True)

    # Generate safe certificate name
    safe_name = f"{name}_{user.username}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        if cert_type == "ca":
            # Generate CA certificate
            process = await asyncio.create_subprocess_exec(
                os.path.join(settings.ATAK_CERT_DIR, "makeRootCa.sh"),
                "--ca-name", safe_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        else:
            # Generate client or server certificate
            process = await asyncio.create_subprocess_exec(
                os.path.join(settings.ATAK_CERT_DIR, "makeCert.sh"),
                cert_type,
                safe_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Certificate generation failed: {stderr.decode()}")

        # Get certificate file paths
        cert_path = os.path.join(settings.ATAK_FILES_DIR, f"{safe_name}.p12")
        
        if not os.path.exists(cert_path):
            raise Exception("Certificate file not found after generation")

        return {
            "file_path": cert_path,
            "name": safe_name
        }

    except Exception as e:
        # Clean up any partially generated files
        cleanup_paths = [
            os.path.join(settings.ATAK_FILES_DIR, f"{safe_name}.p12"),
            os.path.join(settings.ATAK_FILES_DIR, f"{safe_name}.pem"),
            os.path.join(settings.ATAK_FILES_DIR, f"{safe_name}.key")
        ]
        for path in cleanup_paths:
            if os.path.exists(path):
                os.remove(path)
        
        raise Exception(f"Failed to generate certificate: {str(e)}")

async def revoke_certificate(cert_path: str) -> None:
    """
    Revoke a certificate using ATAK's certificate revocation tools.
    
    Args:
        cert_path: Path to the certificate file
    """
    if not os.path.exists(cert_path):
        raise Exception("Certificate file not found")

    try:
        # Get certificate serial number
        process = await asyncio.create_subprocess_exec(
            "openssl",
            "pkcs12",
            "-in", cert_path,
            "-nokeys",
            "-serial",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Failed to get certificate serial: {stderr.decode()}")

        serial = stdout.decode().split("=")[1].strip()

        # Revoke certificate
        process = await asyncio.create_subprocess_exec(
            os.path.join(settings.ATAK_CERT_DIR, "revokeCert.sh"),
            serial,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Certificate revocation failed: {stderr.decode()}")

    except Exception as e:
        raise Exception(f"Failed to revoke certificate: {str(e)}")

async def verify_certificate(cert_path: str) -> bool:
    """
    Verify a certificate's validity.
    
    Args:
        cert_path: Path to the certificate file
    
    Returns:
        bool: True if certificate is valid, False otherwise
    """
    if not os.path.exists(cert_path):
        return False

    try:
        # Verify certificate against CA
        process = await asyncio.create_subprocess_exec(
            "openssl",
            "verify",
            "-CAfile", os.path.join(settings.ATAK_CERT_DIR, "ca.pem"),
            cert_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        return process.returncode == 0

    except Exception:
        return False

async def get_certificate_info(cert_path: str) -> Dict[str, str]:
    """
    Get information about a certificate.
    
    Args:
        cert_path: Path to the certificate file
    
    Returns:
        Dict containing certificate information
    """
    if not os.path.exists(cert_path):
        raise Exception("Certificate file not found")

    try:
        # Get certificate information
        process = await asyncio.create_subprocess_exec(
            "openssl",
            "x509",
            "-in", cert_path,
            "-text",
            "-noout",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Failed to get certificate info: {stderr.decode()}")

        info = stdout.decode()
        
        # Parse relevant information
        return {
            "subject": next((line.strip() for line in info.split('\n') if "Subject:" in line), ""),
            "issuer": next((line.strip() for line in info.split('\n') if "Issuer:" in line), ""),
            "validity": next((line.strip() for line in info.split('\n') if "Not After" in line), ""),
            "serial": next((line.strip() for line in info.split('\n') if "Serial Number:" in line), "")
        }

    except Exception as e:
        raise Exception(f"Failed to get certificate information: {str(e)}")
