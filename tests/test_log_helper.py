from stamps._log import banner, blank_line


def test_banner_matches_csh(capsys):
    banner("mt_prep_snap", "Andy Hooper, August 2017")
    assert capsys.readouterr().out == "mt_prep_snap Andy Hooper, August 2017\n \n"


def test_banner_uses_basename(capsys):
    banner("/abs/path/to/mt_prep_snap", "Andy Hooper, August 2017")
    assert capsys.readouterr().out.startswith("mt_prep_snap ")


def test_blank_line_is_space_newline(capsys):
    blank_line()
    assert capsys.readouterr().out == " \n"
