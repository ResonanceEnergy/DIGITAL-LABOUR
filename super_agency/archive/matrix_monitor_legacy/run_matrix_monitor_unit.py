from tests.test_matrix_monitor_unit import test_matrix_monitor_success, test_matrix_monitor_partial_failures

if __name__ == '__main__':
    print('running unit tests...')
    success1 = test_matrix_monitor_success(None)
    success2 = test_matrix_monitor_partial_failures(None)
    print('success1', success1, 'success2', success2)
    if success1 and success2:
        print('ALL UNIT TESTS PASSED')
        exit(0)
    else:
        print('SOME TESTS FAILED')
        exit(1)
