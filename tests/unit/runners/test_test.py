import pytest
from mock import patch
from srv.modules.runners import test

example_module_return = (True, {}) # the 2nd part of the tuple is not used in this runner (yet?)


@pytest.mark.parametrize("test_input, expected", [({'called_by_orch': True}, [True, True]),
                                                  ({'called_by_runner': True}, [True, True]),
                                                  ({}, 'success')])
@patch('srv.modules.runners.test.exec_module', autospec=True)
def test_good(exec_module_mock, test_input, expected):

    exec_module_mock.side_effect = [
        example_module_return, example_module_return
    ]

    foo = test.good(**test_input)

    exec_module_mock.assert_called_with(
        arguments=['admin'],
        target='roles:mon',
        function='mon',
        module='keyring')
    assert exec_module_mock.call_count == 2
    assert foo == expected


example_module_return_failure = (False, {}) # the 2nd part of the tuple is not used in this runner (yet?)


@pytest.mark.parametrize("test_input, expected", [({'called_by_orch': True}, [False]),
                                                  ({'called_by_runner': True}, [False]),
                                                  ({}, 'failure')])
@patch('srv.modules.runners.test.exec_module', autospec=True)
def test_bad(exec_module_mock, test_input, expected):

    exec_module_mock.side_effect = [example_module_return_failure]

    foo = test.bad(**test_input)

    exec_module_mock.assert_called_with(
        arguments=['admin'],
        target='roles:mon',
        function='mon_failure',
        module='keyring')

    assert exec_module_mock.call_count == 1
    assert foo == expected
