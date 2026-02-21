from app.core.fingerprint import file_fingerprint_md5


def test_file_fingerprint_md5_browser_virtual_path_is_deterministic():
    path = "browser://ball_by_ball_ipl"
    a = file_fingerprint_md5(path)
    b = file_fingerprint_md5(path)
    assert a == b
    assert isinstance(a, str)
    assert len(a) == 32


def test_file_fingerprint_md5_browser_virtual_paths_differ():
    a = file_fingerprint_md5("browser://table_a")
    b = file_fingerprint_md5("browser://table_b")
    assert a != b
