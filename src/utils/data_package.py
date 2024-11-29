import os
import json
import shutil
import uuid
from typing import Dict
from datetime import datetime

from ..config.settings import get_settings
from ..db.models import User, Certificate, DataPackage

settings = get_settings()

async def create_data_package_files(
    package_type: str,
    server_config: Dict,
    manifest_config: Dict,
    certificate: Certificate,
    user: User
) -> str:
    """
    Create ATAK data package files.
    
    Args:
        package_type: Type of package (full, basic, itak)
        server_config: Server configuration
        manifest_config: Manifest configuration
        certificate: Associated certificate
        user: User creating the package
    
    Returns:
        str: Path to the created data package
    """
    # Create unique package directory
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    package_dir = f"data_package_{user.username}_{timestamp}"
    package_path = os.path.join(settings.ATAK_FILES_DIR, package_dir)
    os.makedirs(package_path, exist_ok=True)

    try:
        # Copy appropriate template based on package type
        template_dir = "template-full" if package_type == "full" else "template"
        template_path = os.path.join(settings.ATAK_CERT_DIR, template_dir)
        
        for item in os.listdir(template_path):
            source = os.path.join(template_path, item)
            destination = os.path.join(package_path, item)
            
            if os.path.isdir(source):
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)

        # Copy certificate file if full package
        if package_type == "full":
            cert_destination = os.path.join(package_path, os.path.basename(certificate.file_path))
            shutil.copy2(certificate.file_path, cert_destination)

        # Update configuration files
        await update_package_configs(
            package_path=package_path,
            package_type=package_type,
            server_config=server_config,
            manifest_config=manifest_config,
            certificate=certificate
        )

        # Create zip file
        zip_path = f"{package_path}.zip"
        if package_type == "itak":
            # iTAK specific packaging
            suffix = '_iTAK'
            os.chdir(package_path)
            os.rename('secure.pref', 'config.pref')
            shutil.make_archive(f"{package_path}{suffix}", 'zip', package_path, 
                              base_dir=None, 
                              include_files=['config.pref', '*.p12'])
            zip_path = f"{package_path}{suffix}.zip"
        else:
            # Standard packaging
            shutil.make_archive(package_path, 'zip', package_path)

        # Cleanup temporary directory
        shutil.rmtree(package_path)
        
        return zip_path

    except Exception as e:
        # Cleanup on failure
        if os.path.exists(package_path):
            shutil.rmtree(package_path)
        raise Exception(f"Failed to create data package: {str(e)}")

async def update_package_configs(
    package_path: str,
    package_type: str,
    server_config: Dict,
    manifest_config: Dict,
    certificate: Certificate
) -> None:
    """
    Update configuration files in a data package.
    
    Args:
        package_path: Path to the data package directory
        package_type: Type of package (full, basic, itak)
        server_config: Server configuration
        manifest_config: Manifest configuration
        certificate: Associated certificate
    """
    # Update preference file
    pref_file = os.path.join(package_path, 'secure.pref')
    if os.path.exists(pref_file):
        with open(pref_file, 'r') as f:
            content = f.read()

        # Replace configuration placeholders
        content = content.replace('##hostname##', f"{server_config['hostname']}:{server_config['port']}")
        content = content.replace('##protocol##', server_config['protocol'])
        
        if package_type == "full":
            content = content.replace('##caLocation##', os.path.basename(certificate.file_path))

        with open(pref_file, 'w') as f:
            f.write(content)

    # Update manifest file
    manifest_file = os.path.join(package_path, 'MANIFEST', 'manifest.xml')
    if os.path.exists(manifest_file):
        with open(manifest_file, 'r') as f:
            content = f.read()

        # Replace manifest placeholders
        content = content.replace('##uuid##', str(uuid.uuid4()))
        for key, value in manifest_config.items():
            content = content.replace(f'##{key}##', str(value))

        with open(manifest_file, 'w') as f:
            f.write(content)

async def update_data_package_files(
    package: DataPackage,
    server_config: Dict,
    manifest_config: Dict
) -> None:
    """
    Update existing data package files.
    
    Args:
        package: DataPackage model instance
        server_config: New server configuration
        manifest_config: New manifest configuration
    """
    # Extract existing package
    package_dir = package.file_path.replace('.zip', '')
    os.makedirs(package_dir, exist_ok=True)
    
    try:
        # Extract existing package
        shutil.unpack_archive(package.file_path, package_dir, 'zip')

        # Update configurations
        await update_package_configs(
            package_path=package_dir,
            package_type=package.package_type,
            server_config=server_config,
            manifest_config=manifest_config,
            certificate=package.certificate
        )

        # Repackage
        if package.package_type == "itak":
            suffix = '_iTAK'
            os.chdir(package_dir)
            os.rename('secure.pref', 'config.pref')
            shutil.make_archive(f"{package_dir}{suffix}", 'zip', package_dir,
                              base_dir=None,
                              include_files=['config.pref', '*.p12'])
        else:
            shutil.make_archive(package_dir, 'zip', package_dir)

        # Cleanup
        shutil.rmtree(package_dir)

    except Exception as e:
        # Cleanup on failure
        if os.path.exists(package_dir):
            shutil.rmtree(package_dir)
        raise Exception(f"Failed to update data package: {str(e)}")

def validate_package_structure(package_path: str) -> bool:
    """
    Validate the structure of a data package.
    
    Args:
        package_path: Path to the data package directory
    
    Returns:
        bool: True if valid, False otherwise
    """
    required_files = [
        'secure.pref',
        os.path.join('MANIFEST', 'manifest.xml')
    ]

    for file_path in required_files:
        if not os.path.exists(os.path.join(package_path, file_path)):
            return False

    return True
