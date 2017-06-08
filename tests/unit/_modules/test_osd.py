import pytest
from srv.salt._modules import osd
from mock import MagicMock, patch, mock

class TestOSDInstanceMethods():
    '''
    This class contains a set of functions that test srv.salt._modules.osd
    '''
    @mock.patch('srv.salt._modules.osd.glob')
    def test_paths(self, glob):
        glob.return_value.glob = []
        ret = osd.paths()
        glob.glob.assert_called_once()
        glob.glob.assert_called_with('/var/lib/ceph/osd/*')
        assert type(ret) is list

    @mock.patch('srv.salt._modules.osd.glob')
    def test_devices(self, glob):
        glob.return_value.glob = []
        ret = osd.devices()
        glob.glob.assert_called_once()
        glob.glob.assert_called_with('/var/lib/ceph/osd/*')
        assert type(ret) is list

    @mock.patch('srv.salt._modules.osd.glob')
    def test_pairs(self, glob):
        glob.return_value.glob = []
        ret = osd.pairs()
        glob.glob.assert_called_once()
        glob.glob.assert_called_with('/var/lib/ceph/osd/*')
        assert type(ret) is list

    @pytest.mark.skip(reason="Postponed to later")
    def test_filter_devices(self):
        pass

    @pytest.mark.skip(reason="about to be refactored")
    def test_configured(self):
        pass

    @mock.patch('srv.salt._modules.osd.glob')
    def test_list_(self, glob):
        glob.return_value.glob = []
        osd.__grains__ = {'ceph': {'foo': 'mocked_grain'}}
        ret = osd.list_()
        glob.glob.assert_called_once()
        glob.glob.assert_called_with('/var/lib/ceph/osd/*/fsid')
        assert 'foo' in ret
        assert type(ret) is list
        osd.__grains__ = {}

    @mock.patch('srv.salt._modules.osd.glob')
    def test_list_no_grains(self, glob):
        glob.return_value.glob = []
        ret = osd.list_()
        glob.glob.assert_called_once()
        glob.glob.assert_called_with('/var/lib/ceph/osd/*/fsid')
        assert type(ret) is list

    def test_readlink(self):
        pass


class TetstOSDState():
    pass


class TestOSDWeight():
    pass


class TestOSDConfig():

    osd.__pillar__ = {}
    osd.__salt__ = {'mine.get': MagicMock()}
    osd.__grains__ = {'id': 1}

    @pytest.fixture(scope='class')
    def osd_o(self):
        with patch.object(osd.OSDConfig, 'construct', lambda self: None):
            cnf = osd.OSDConfig('/dev/sdx')
            yield cnf

    def test__set_tli(self):
        pass

    def test_convert_tli(self):
        pass

    def test_set_bytes(self, osd_o):  
        osd.__grains__ = {'id': 1}
        test = osd_o.set_bytes()
        import pdb;pdb.set_trace()

