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
    osd.__salt__ = {'mine.get': lambda tgt, fun: {1:1}}
    osd.__grains__ = {'id': 1}

    # How to properly reset the salt_internals after it was altered..
    # fixtures allow you to teardown the fixture..
    # can you yield multiple things?
    @pytest.fixture(scope='class')
    def salt_internals(self):
        osd.__pillar__ = {}
        osd.__salt__ = {'mine.get': 'asd'}
        osd.__grains__ = {'id': 1}

    @pytest.fixture(scope='class')
    def osd_o(self):
        with patch.object(osd.OSDConfig, 'construct', lambda self: None):
            print "Constructing the OSDConfig object"
            cnf = osd.OSDConfig('/dev/sdx')
            yield cnf
            # everything after the yield is a teardown code
            print "Teardown OSDConfig object"

    def test__set_tli(self):
        pass

    def test_convert_tli(self):
        pass

    def test_set_bytes_valid(self, osd_o):  
        osd.__grains__ = {'id': 'data1.ceph'}
        cephdisks_out = {'data1.ceph': [{'Device File': '/dev/sdx', 'Bytes': 1000000}]}
        osd.__salt__ = {'mine.get': lambda tgt, fun: cephdisks_out}
        ret = osd_o.set_bytes()
        assert type(ret) is int
        assert ret == 1000000

    def test_set_bytes_invalid(self, osd_o):  
        osd.__grains__ = {'id': 'data1.ceph'}
        cephdisks_out = {}
        osd.__salt__ = {'mine.get': lambda tgt, fun: cephdisks_out}
        with pytest.raises(RuntimeError) as excinfo:
            osd_o.set_bytes()
            assert 'Mine on data1.ceph' in str(excinfo.value)

    def test_set_capacity(self, osd_o):  
        osd.__grains__ = {'id': 'data1.ceph'}
        cephdisks_out = {'data1.ceph': [{'Device File': '/dev/sdx', 'Capacity': 1000000}]}
        osd.__salt__ = {'mine.get': lambda tgt, fun: cephdisks_out}
        osd.__grains__ = {'id': 'data1.ceph'}
        ret = osd_o.set_capacity()
        assert ret == 1000000

    def test_set_capacity_invalid(self, osd_o):  
        osd.__grains__ = {'id': 'data1.ceph'}
        cephdisks_out = {}
        osd.__salt__ = {'mine.get': lambda tgt, fun: cephdisks_out}
        osd.__grains__ = {'id': 'data1.ceph'}
        with pytest.raises(RuntimeError) as excinfo:
            osd_o.set_capacity()
            assert 'Mine on data1.ceph' in str(excinfo.value)

    def test_small_size_false(self, osd_o):
        osd_o.size = 10000000000
        ret = osd_o._set_small()
        assert ret is False

    def test_small_size_true(self, osd_o):
        osd_o.size = 1
        ret = osd_o._set_small()
        assert ret is True

    def test_config_version_old(self, osd_o):
        osd.__pillar__ = {'storage': {'osds': '1'}}
        ret = osd_o._config_version()
        assert ret == 'v1'

    def test_config_version_new(self, osd_o):
        osd.__pillar__ = {'ceph': {'storage': '1'}}
        ret = osd_o._config_version()
        assert ret == 'v2'

    @mock.patch('srv.salt._modules.osd.OSDConfig._config_version')
    def test_set_format_filestore(self, conf_mock, osd_o):
        conf_mock.return_value = 'v1'
        ret = osd_o.set_format()
        assert ret is 'filestore'

    @mock.patch('srv.salt._modules.osd.OSDConfig._config_version')
    def test_set_format_bluestore_custom(self, conf_mock, osd_o):
        conf_mock.return_value = 'v2'
        osd_o.tli = {'/dev/sdx': {'format': 'custom_store'}}
        ret = osd_o.set_format()
        assert ret is 'custom_store'

    @mock.patch('srv.salt._modules.osd.OSDConfig._config_version')
    def test_set_format_bluestore_default(self, conf_mock, osd_o):
        osd_o.tli = {'/dev/sdx': {}}
        conf_mock.return_value = 'v2'
        ret = osd_o.set_format()
        assert ret is 'bluestore'

    @mock.patch('srv.salt._modules.osd.OSDConfig._config_version')
    def test_set_format_raise(self, conf_mock, osd_o):
        conf_mock.return_value = 'v3'
        with pytest.raises(BaseException) as excinfo:
            osd_o.set_format()
            assert 'Mine on data1.ceph' in str(excinfo.value)

    @mock.patch('srv.salt._modules.osd.OSDConfig._config_version')
    def test_set_journal(self, osd_o) 
        conf_mock.return_value = 'v1'
