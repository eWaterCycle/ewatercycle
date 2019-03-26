from ewatercycle.parametersetdb.datafiles import SymlinkCopier


def test_SymlinkCopier(tmp_path):
    source_dir = tmp_path / 'source'
    source_dir.mkdir()
    source_forcings = source_dir / 'forcings.csv'
    source_forcings.write_text('dummy')
    copier = SymlinkCopier(str(source_dir))

    target_dir = tmp_path / 'target'
    copier.save(target_dir)

    target_forcings = target_dir / 'forcings.csv'
    assert target_forcings.read_text() == 'dummy'
