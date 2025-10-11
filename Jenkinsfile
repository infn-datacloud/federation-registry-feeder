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
        stage("Tests") {
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
                                        sh '''
                                            python -m ensurepip --upgrade && python -m pip install --upgrade pip poetry setuptools
                                            poetry install
                                        '''
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
                                        sh '''
                                            python -m ensurepip --upgrade && python -m pip install --upgrade pip poetry setuptools
                                            pip install -r requirements.txt
                                        '''
                                    }
                                }
                            }
                            stage("Run Tests") {
                                steps {
                                    script {
                                        echo "Running tests on python${PYTHON_VERSION}"
                                        configFileProvider([configFile(fileId: ".coveragerc", variable: 'COVERAGERC')]) {
                                            sh """
                                                COVERAGE_FILE=coverage-reports/.coverage-${PYTHON_VERSION} \
                                                pytest \
                                                --cov \
                                                --cov-config=${COVERAGERC} \
                                                --cov-report=xml:coverage-reports/coverage-${PYTHON_VERSION}.xml \
                                                --cov-report=html:coverage-reports/htmlcov-${PYTHON_VERSION}
                                            """
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
                }
            }
        }
        stage("Combine coverages") {
            agent {
                docker {
                    label 'jenkins-node-label-1'
                    image "python:3.13"
                    args "-u root:root"
                    reuseNode true
                }
            }
            steps {
                script {
                    echo 'Merge coverage reports'
                    sh '''
                        pip install coverage
                        coverage combine coverage-reports/.coverage-*
                        coverage xml -o coverage.xml
                    '''
                }
            }
            post {
                success {
                    script {
                        archiveArtifacts artifacts: "coverage.xml", fingerprint: true
                    }
                }
            }
        }
        stage("Notify SonarCloud") {
            agent {
                docker {
                    label 'jenkins-node-label-1'
                    image 'sonarsource/sonar-scanner-cli'
                    args '-u root:root -v ${WORKSPACE}:/usr/src'
                    reuseNode true
                }
            }
            steps {
                withSonarQubeEnv('SonarCloud') {
                    echo 'Sends coverage report to SonarCloud'
                    sh '''
                        sonar-scanner \
                        -D sonar.projectKey=infn-datacloud_${PROJECT_NAME} \
                        -D sonar.organization=infn-datacloud \
                        -D sonar.sources=src \
                        -D sonar.tests=tests \
                        -D sonar.branch.name=${BRANCH_NAME} \
                        -D sonar.python.coverage.reportPaths=coverage.xml
                    '''
                }
            }
        }
    //     stage("Build images") {
    //         when {
    //             expression { currentBuild.result != 'UNSECURE' }
    //         }
    //         matrix {
    //             axes {
    //                 axis {
    //                     name 'PYTHON_VERSION'
    //                     values '3.10', '3.11', '3.12', '3.13'
    //                 }
    //             }
    //             stages {
    //                 stage("Build") {
    //                     steps {
    //                         script {
    //                             echo "Build docker image for python${PYTHON_VERSION}"
    //                             // dockerImg = dockerRepository.buildImage(
    //                             //     imageName: env.PROJECT_NAME,
    //                             //     dockerfile: env.DOCKERFILE,
    //                             //     pythonVersion: env.PYTHON_VERSION
    //                             // )
    //                         }
    //                     }
    //                 }
    //             }
    //         }
    //     }
    // }
    // post {
    //     always {
    //         echo 'Cleaning up Docker images...'
    //         sh 'docker system prune -af || true'
    //     }
    }
}
