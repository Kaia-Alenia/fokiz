import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

def test_installation_equivalence():
    with tempfile.TemporaryDirectory() as home_install, tempfile.TemporaryDirectory() as home_init:
        env_install = os.environ.copy()
        env_install['HOME'] = home_install
        subprocess.run([sys.executable, 'install.py'], input='y\ny\n', text=True, env=env_install, cwd=str(Path(__file__).parent.parent))
        env_init = os.environ.copy()
        env_init['HOME'] = home_init
        subprocess.run([sys.executable, '-m', 'app.cli', 'init'], input='TestName\ny\n', text=True, env=env_init, cwd=str(Path(__file__).parent.parent / 'src'))
        files_to_compare = [('.local/bin/fokiz', '.local/bin/fokiz'), ('.local/bin/fokiz-monitor', '.local/bin/fokiz-monitor'), ('.config/systemd/user/fokiz-monitor.service', '.config/systemd/user/fokiz-monitor.service'), ('.config/systemd/user/fokiz-monitor.timer', '.config/systemd/user/fokiz-monitor.timer')]
        for p_rel_install, p_rel_init in files_to_compare:
            p_install = Path(home_install) / p_rel_install
            p_init = Path(home_init) / p_rel_init
            assert p_install.exists(), f'Missing file from install.py: {p_install}'
            assert p_init.exists(), f'Missing file from init.py: {p_init}'
            content_install = p_install.read_text().replace(home_install, '<HOME>')
            content_init = p_init.read_text().replace(home_init, '<HOME>')
            assert content_install == content_init, f'Mismatch in {p_rel_install}\nInstall:\n{content_install}\n\nInit:\n{content_init}'
        for p_rel in ['.config/systemd/user/fokiz.service', '.config/systemd/user/fokiz.timer']:
            assert not (Path(home_install) / p_rel).exists()
            assert not (Path(home_init) / p_rel).exists()
    print('Equivalence test passed successfully.')
if __name__ == '__main__':
    test_installation_equivalence()
