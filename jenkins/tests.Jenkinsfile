#!groovy
@Library('jenkins-libraries') _

pipeline {
    agent { label 'jenkinsworker00' }

    environment {
        COVERAGE_DIR = 'coverage-reports'
        SONAR_HOST = 'https://sonarcloud.io'
        SONAR_ORGANIZATION = 'infn-datacloud'
        SONAR_PROJECT = 'federation-registry-feeder'
        SONAR_TOKEN = credentials('sonar-token')
    }

    stages {
        stage('Run tests on multiple python versions') {
            parallel {
                stage('Run on tests on python3.10') {
                    steps {
                        script {
                            pythonProject.testCode(
                                '3.10',
                                '',
                                '.coveragerc',
                                "${COVERAGE_DIR}"
                                )
                        }
                    }
                }
                stage('Run on tests on python3.11') {
                    steps {
                        script {
                            pythonProject.testCode(
                                '3.11',
                                '',
                                '.coveragerc',
                                "${COVERAGE_DIR}"
                                )
                        }
                    }
                }
            }
        }
    }
    post {
        always {
            script {
                sonar.analysis(
                    "${SONAR_TOKEN}",
                    "${SONAR_PROJECT}",
                    "${SONAR_ORGANIZATION}",
                    "${SONAR_HOST}",
                    "${COVERAGE_DIR}",
                    'src',
                    'tests',
                    '3.10, 3.11'
                )
            }
        }
    }
}
