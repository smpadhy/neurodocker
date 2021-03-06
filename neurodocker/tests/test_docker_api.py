"""Tests for neurodocker.docker_api"""
# Author: Jakub Kaczmarzyk <jakubk@mit.edu>
from __future__ import absolute_import
from io import BytesIO
import os
import threading
import time

import docker
import pytest

from neurodocker.docker_api import (docker_is_running, Dockerfile, DockerImage,
                                    DockerContainer, RawOutputLogger,
                                    require_docker)
from neurodocker.interfaces import ANTs, FSL, Miniconda, SPM

client = docker.from_env()


def test_docker_is_running():
    assert docker_is_running(client), "Docker is not running"


class TestDockerfile(object):

    @pytest.fixture(autouse=True)
    def setup(self, tmpdir):
        self.tmpdir = tmpdir
        self.specs = {'base': 'ubuntu:16.04',
                      'conda_env': {'python_version': '3.5.1',
                                    'conda_install': 'numpy',
                                    'pip_install': 'pandas'},
                      'software': {'ants': {'use_binaries': True, 'version': '2.1.0'}}}

        base = "FROM {}".format(self.specs['base'])
        noninteractive = "ARG DEBIAN_FRONTEND=noninteractive"
        miniconda = Miniconda(pkg_manager='apt', **self.specs['conda_env']).cmd
        ants = ANTs(pkg_manager='apt', **self.specs['software']['ants']).cmd
        self.full = "\n\n".join((base, noninteractive, miniconda, ants))

    def test_init(self):
        assert Dockerfile(self.specs, 'apt').cmd == self.full, "error creating Dockerfile"

    def test_save(self):
        dockerfile_path = os.path.join(self.tmpdir.strpath, 'Dockerfile')
        Dockerfile(self.specs, 'apt').save(filepath=dockerfile_path)

        assert len(self.tmpdir.listdir()) == 1, "file not saved"

        content = self.tmpdir.join("Dockerfile").read()
        assert content == self.full + "\n", "error in saved Dockerfile"


class TestRawOutputLogger(object):
    @pytest.fixture(autouse=True)
    def setup(self, tmpdir):
        self.tmpdir = tmpdir

    def test_start(self):
        cmd = "FROM alpine:latest"
        cmd = cmd.encode('utf-8')
        cmd = BytesIO(cmd)
        logs = client.api.build(fileobj=cmd, rm=True)
        logger = RawOutputLogger(logs)
        logger.daemon = True
        logger.start()

        assert logger.is_alive(), "RawOutputLogger not alive!"

        while logger.is_alive():
            pass

        image = client.images.get(logger.id)
        assert isinstance(image, docker.models.images.Image), "image is not a Docker image!"
