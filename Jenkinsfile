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
        SONAR_TOKEN = credentials('sonar-token')
    }

    triggers {
        cron("${myCron.periodicTrigger(env.BRANCH_NAME)}")
    }

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
                                args "-u root:root -e POETRY_VERSION=${POETRY_VERSION} -e POETRY_VIRTUALENVS_CREATE=false"
                                reuseNode true
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
                                        sh 'poetry install'
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
                                    always {
                                        script {
                                            archiveArtifacts artifacts: "coverage-reports/**/*", fingerprint: true
                                        }
                                    }
                                }
                            }
                        }
                    }
                    stage("Notify SonarCloud") {
                        steps {
                            script {
                                sh '''docker run --rm \
                                    -e SONAR_HOST_URL=https://sonarcloud.io/ \
                                    -e SONAR_TOKEN=${SONAR_TOKEN} \
                                    -v ${WORKSPACE}:/usr/src \
                                    sonarsource/sonar-scanner-cli \
                                    -D sonar.projectKey=infn-datacloud_${PROJECT_NAME} \
                                    -D sonar.organization=infn-datacloud \
                                    -D sonar.sources=src \
                                    -D sonar.tests=tests \
                                    -D sonar.branch.name=${BRANCH_NAME} \
                                    -D sonar.python.version='${PYTHON_VERSION}' \
                                    -D sonar.python.coverage.reportPaths=coverage-reports/coverage-${PYTHON_VERSION}.xml'''
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
