#!groovy
@Library('jenkins-libraries') _

pipeline {
    agent {
        node {
            label 'jenkins-node-label-1'
        }
    }

    environment {
        PROJECT_NAME = 'federation-registry-feeder'
        DOCKERFILE = './docker/Dockerfile'
        USE_POETRY = true
        POETRY_VERSION = '2.1'
    }

    // triggers {
    //     cron("${myCron.periodicTrigger(env.BRANCH_NAME)}")
    // }

    stages {
        stage("Test and build docker") {
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.10', '3.11', '3.12', '3.13'
                    }
                }
                stages {
                    stage("Test"){
                        agent {
                            docker {
                                label 'jenkins-node-label-1'
                                image "python:${PYTHON_VERSION}"
                                args "-u root:root"
                            }
                        }
                        stages{
                            stage("Install dependencies with poetry") {
                                when { 
                                    expression { env.USE_POETRY }
                                }
                                steps {
                                    script  {
                                        echo "Installing dependencies using poetry on python${PYTHON_VERSION}"
                                        sh 'python -m ensurepip --upgrade && python -m pip install --upgrade pip poetry setuptools'
                                        sh "POETRY_VERSION=${POETRY_VERSION} POETRY_VIRTUALENVS_CREATE=false poetry install"
                                    }
                                }
                            }
                            stage("Install dependencies with pip") {
                                when { 
                                    expression { !env.USE_POETRY }
                                }
                                steps {
                                    script  {
                                        echo "Installing dependencies using pip on python${PYTHON_VERSION}"
                                        sh 'python -m ensurepip --upgrade && python -m pip install --upgrade pip poetry setuptools'
                                        sh 'pip install -r requirements.txt'
                                    }
                                }
                            }
                            stage("Run Tests") {
                                steps {
                                    script {
                                        echo "Running tests on python${PYTHON_VERSION}"
                                        configFileProvider([configFile(fileId: ".coveragerc", variable: 'COVERAGERC')]) {
                                            sh """pytest \
                                            --cov \
                                            --cov-config=${COVERAGERC} \
                                            --cov-report=xml:coverage-reports/coverage-${PYTHON_VERSION}.xml \
                                            --cov-report=html:coverage-reports/htmlcov-${PYTHON_VERSION}"""
                                        }
                                    }
                                }
                                post {
                                    success {
                                        script {
                                            archiveArtifacts artifacts: "coverage-reports/**/*", fingerprint: true
                                            // pythonTests.notifySonar(
                                            //     token: "${SONAR_TOKEN}",
                                            //     project: env.PROJECT_NAME,
                                            //     pythonVersion: env.PYTHON_VERSION,
                                            //     srcDir: 'src'
                                            // )
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // stage("Build docker image") {
                    //     steps {
                    //         script {
                    //             echo "Build docker image for python${PYTHON_VERSION}"
                    //             dockerImg = dockerRepository.buildImage(
                    //                 imageName: env.PROJECT_NAME,
                    //                 dockerfile: env.DOCKERFILE,
                    //                 pythonVersion: env.PYTHON_VERSION
                    //             )
                    //         }
                    //     }
                    // }
                }
            }
        }
    }
    // post {
    //     always {
    //         echo 'Cleaning up Docker images...'
    //         sh 'docker system prune -af || true'
    //     }
    // }
}
