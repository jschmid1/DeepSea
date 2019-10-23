import pytest
from mock import patch
from srv.modules.runners import test



@patch('srv.modules.runners.test.exec_module', autospec=True, return_value=('True', {'foo': 'bar'}))
def test_good(exec_module_mock):
    foo = test.good()
    import pdb;pdb.set_trace()
