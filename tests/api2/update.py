#!/usr/bin/env python3.6

# Author: Eric Turgeon
# License: BSD

import pytest
import sys
import os
apifolder = os.getcwd()
sys.path.append(apifolder)
from functions import GET, POST, vm_state, vm_start, ping_host
from auto_config import vm_name, interface, ip
from time import sleep, time


def test_01_get_initial_FreeNAS_version():
    results = GET("/system/info/")
    assert results.status_code == 200, results.text
    assert isinstance(results.json(), dict) is True, results.text
    global initial_version
    initial_version = results.json()['version']


def test_02_get_update_trains():
    results = GET('/update/get_trains/')
    assert results.status_code == 200, results.text
    assert isinstance(results.json(), dict) is True, results.text
    global selected_trains
    selected_trains = results.json()['selected']


def test_03_check_available_update():
    global upgrade
    results = POST('/update/check_available/')
    assert results.status_code == 200, results.text
    assert isinstance(results.json(), dict) is True, results.text
    if results.json() == {}:
        upgrade = False
    else:
        upgrade = True


def test_04_update_get_pending():
    results = POST('/update/get_pending/')
    assert results.status_code == 200, results.text
    assert isinstance(results.json(), list) is True, results.text
    assert results.json() == [], results.text


def test_05_get_download_update():
    if upgrade is False:
        pytest.skip('No update found')
    else:
        results = GET('/update/download/')
        global JOB_ID
        assert results.status_code == 200, results.text
        assert isinstance(results.json(), int) is True, results.text
        JOB_ID = results.json()


def test_06_verify_the_update_download_is_successful():
    if upgrade is False:
        pytest.skip('No update found')
    else:
        global download_hang
        stop_time = time() + 600
        download_hang = False
        while True:
            get_job = GET(f'/core/get_jobs/?id={JOB_ID}')
            job_status = get_job.json()[0]
            if job_status['state'] in ('RUNNING', 'WAITING'):
                if stop_time <= time():
                    download_hang = True
                    assert False, get_job.text
                    break
                sleep(5)
            else:
                assert job_status['state'] == 'SUCCESS', get_job.text
                break


def test_07_get_pending_update():
    if upgrade is False:
        pytest.skip('No update found')
    elif download_hang is True:
        pytest.skip(f'Downloading {selected_trains} failed')
    else:
        results = POST('/update/get_pending/')
        assert results.status_code == 200, results.text
        assert isinstance(results.json(), list) is True, results.text
        assert results.json() != [], results.text


def test_08_install_update():
    if upgrade is False:
        pytest.skip('No update found')
    elif download_hang is True:
        pytest.skip(f'Downloading {selected_trains} failed')
    else:
        if vm_name is None and interface == 'vtnet0':
            reboot = False
        else:
            reboot = True
        payload = {
            "train": selected_trains,
            "reboot": reboot
        }
        results = POST('/update/update/', payload)
        global JOB_ID
        assert results.status_code == 200, results.text
        assert isinstance(results.json(), int) is True, results.text
        JOB_ID = results.json()


def test_09_verify_the_update_is_successful():
    if upgrade is False:
        pytest.skip('No update found')
    elif download_hang is True:
        pytest.skip(f'Downloading {selected_trains} failed')
    else:
        while True:
            get_job = GET(f'/core/get_jobs/?id={JOB_ID}')
            job_status = get_job.json()[0]
            if job_status['state'] in ('RUNNING', 'WAITING'):
                sleep(5)
            else:
                assert job_status['state'] == 'SUCCESS', get_job.text
                break


def test_10_verify_system_is_ready_to_reboot():
    if upgrade is False:
        pytest.skip('No update found')
    elif download_hang is True:
        pytest.skip(f'Downloading {selected_trains} failed')
    else:
        results = POST('/update/check_available/')
        assert results.status_code == 200, results.text
        assert isinstance(results.json(), dict) is True, results.text
        assert results.json()['status'] == 'REBOOT_REQUIRED', results.text


def test_11_wait_for_first_reboot_with_bhyve():
    if upgrade is False:
        pytest.skip('No update found')
    else:
        if vm_name is None:
            pytest.skip('skip no vm_name')
        else:
            while vm_state(vm_name) != 'stopped':
                sleep(5)
            assert vm_start(vm_name) is True
    sleep(1)


def test_12_wait_for_second_reboot_with_bhyve():
    if upgrade is False:
        pytest.skip('No update found')
    else:
        if vm_name is None:
            pytest.skip('skip no vm_name')
        else:
            while vm_state(vm_name) != 'stopped':
                sleep(5)
            assert vm_start(vm_name) is True
    sleep(1)


def test_13_wait_for_FreeNAS_to_be_online():
    if upgrade is False:
        pytest.skip('No update found')
    else:
        while ping_host(ip) is not True:
            sleep(5)
        assert ping_host(ip) is True
    sleep(10)


def test_14_verify_initial_version_is_not_current_FreeNAS_version():
    if upgrade is False:
        pytest.skip('No update found')
    else:
        results = GET("/system/info/")
        assert results.status_code == 200, results.text
        assert isinstance(results.json(), dict) is True, results.text
        global current_version
        current_version = results.json()
        assert initial_version != current_version, results.json()
