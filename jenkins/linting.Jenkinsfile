void lintCode(String pythonVersion) {
    docker.image("ghcr.io/withlogicco/poetry:1.8.3-python-$pythonVersion-slim")
        .inside('-e POETRY_VIRTUALENVS_IN_PROJECT=true -u root:root') {
            sh 'poetry install'
            sh 'ruff check ./src'
            sh 'ruff format --check .'
    }
}

pipeline {
    agent { label 'jenkinsworker00' }
    stages {
        stage('Run tests') {
            parallel {
                stage('Python 3.10') {
                    steps {
                        lintCode('3.10')
                    }
                }
                stage('Python 3.11') {
                    steps {
                        lintCode('3.11')
                    }
                }
            }
        }
    }
}
