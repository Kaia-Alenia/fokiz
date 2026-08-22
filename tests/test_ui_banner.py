import os
from pathlib import Path
from app import ui

def test_fokiz_art_exists_and_loads():
    src_app = Path(__file__).parent.parent / 'src' / 'app'
    art_path = src_app / 'fokiz_art.txt'
    assert art_path.exists(), f'Missing CLI art file: {art_path}. fokiz.svg is NOT a replacement.'
    banner_large = ui.render_banner(size='LARGE')
    assert '⢀⡴⢦⡀' in banner_large or '⣿' in banner_large, 'Banner did not load the original fokiz_art.txt content.'
    assert 'FOKIZ' in banner_large
