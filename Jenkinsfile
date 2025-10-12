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
        ORG_NAME = 'infn-datacloud'
        DOCKERFILE = './docker/Dockerfile'
        POETRY_VERSION = '2.1'
        SRC_DIR = 'src'
    }

    triggers {
        cron("${myCron.periodicTrigger(env.BRANCH_NAME)}")
    }

    stages {
        // stage("Tests execution") {
        //     matrix {
        //         axes {
        //             axis {
        //                 name 'PYTHON_VERSION'
        //                 values '3.10', '3.11', '3.12', '3.13'
        //             }
        //         }
        //         stages {
        //             stage("Test"){
        //                 agent {
        //                     docker {
        //                         label 'jenkins-node-label-1'
        //                         image "python:${PYTHON_VERSION}"
        //                         args "-u root:root -e POETRY_VERSION=${POETRY_VERSION} -e POETRY_VIRTUALENVS_CREATE=false"
        //                         reuseNode true
        //                     }
        //                 }
        //                 stages{
        //                     stage("Install dependencies with poetry") {
        //                         when { 
        //                             expression { env.POETRY_VERSIOn != '' }
        //                         }
        //                         steps {
        //                             script  {
        //                                 echo "Installing dependencies using poetry on python${PYTHON_VERSION}"
        //                                 sh '''
        //                                     python -m ensurepip --upgrade
        //                                     python -m pip install --upgrade pip poetry setuptools
        //                                     poetry install
        //                                 '''
        //                             }
        //                         }
        //                     }
        //                     stage("Install dependencies with pip") {
        //                         when { 
        //                             expression { env.POETRY_VERSION == '' }
        //                         }
        //                         steps {
        //                             script  {
        //                                 echo "Installing dependencies using pip on python${PYTHON_VERSION}"
        //                                 sh '''
        //                                     python -m ensurepip --upgrade
        //                                     python -m pip install --upgrade pip poetry setuptools
        //                                     pip install -r requirements.txt
        //                                 '''
        //                             }
        //                         }
        //                     }
        //                     stage("Run Tests") {
        //                         steps {
        //                             script {
        //                                 echo "Running tests on python${PYTHON_VERSION}"
        //                                 configFileProvider([configFile(fileId: ".coveragerc", variable: 'COVERAGERC')]) {
        //                                     sh """
        //                                         COVERAGE_FILE=coverage-reports/.coverage-${PYTHON_VERSION} \
        //                                         pytest \
        //                                         --cov \
        //                                         --cov-config=${COVERAGERC} \
        //                                         --cov-report=xml:coverage-reports/coverage-${PYTHON_VERSION}.xml \
        //                                         --cov-report=html:coverage-reports/htmlcov-${PYTHON_VERSION}
        //                                     """
        //                                 }
        //                             }
        //                         }
        //                         post {
        //                             always {
        //                                 script {
        //                                     archiveArtifacts artifacts: "coverage-reports/**/*", fingerprint: true
        //                                 }
        //                             }
        //                         }
        //                     }
        //                 }
        //             }
        //         }
        //     }
        // }
        // stage("Combine coverages") {
        //     agent {
        //         docker {
        //             label 'jenkins-node-label-1'
        //             image 'python:3.13'
        //             args '-u root:root'
        //             reuseNode true
        //         }
        //     }
        //     steps {
        //         script {
        //             echo 'Merge coverage reports'
        //             sh '''
        //                 pip install coverage
        //                 coverage combine coverage-reports/.coverage-*
        //                 coverage xml -o coverage.xml
        //             '''
        //         }
        //     }
        //     post {
        //         success {
        //             script {
        //                 archiveArtifacts artifacts: "coverage.xml", fingerprint: true
        //             }
        //         }
        //     }
        // }
        // stage("Notify SonarCloud") {
        //     agent {
        //         docker {
        //             label 'jenkins-node-label-1'
        //             image 'sonarsource/sonar-scanner-cli'
        //             args "-u root:root -v ${WORKSPACE}:/usr/src"
        //             reuseNode true
        //         }
        //     }
        //     steps {
        //         withSonarQubeEnv('SonarCloud') {
        //             echo 'Sends coverage report to SonarCloud'
        //             sh """
        //                 sonar-scanner \
        //                 -D sonar.projectKey=${ORG_NAME}_${PROJECT_NAME} \
        //                 -D sonar.organization=${ORG_NAME} \
        //                 -D sonar.sources=${SRC_DIR} \
        //                 -D sonar.tests=tests \
        //                 -D sonar.branch.name=${BRANCH_NAME} \
        //                 -D sonar.python.coverage.reportPaths=coverage.xml
        //             """
        //         }
        //     }
        // }
        stage("Build images") {
            when {
                expression { currentBuild.currentResult == 'SUCCESS' }
            }
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.10', '3.11', '3.12', '3.13'
                    }
                }
                stages {
                    stage("Build") {
                        steps {
                            script {
                                echo "Build docker image for python${PYTHON_VERSION}"
                                def name = "${PROJECT_NAME}"
                                def customTags = []
                                def buildArgsStr = ''
                                if ("${PYTHON_VERSION}" != '') {
                                    buildArgsStr += " --build-arg PYTHON_VERSION=${PYTHON_VERSION}"
                                    customTags.add("python${PYTHON_VERSION}")
                                }
                                if ("${POETRY_VERSION}" != '') {
                                    buildArgsStr += " --build-arg POETRY_VERSION=${POETRY_VERSION}"
                                }
                                if (customTags.size() > 0) {
                                    def tags = customTags.join('-')
                                    name += ":${tags}"
                                }
                                sh "docker build -t ${name} -f ${DOCKERFILE} ${buildArgsStr} ."
                                sh "docker save ${name} -o ${PROJECT_NAME}-${PYTHON_VERSION}.tar"
                                stash includes: "${PROJECT_NAME}-${PYTHON_VERSION}.tar", name: "${PROJECT_NAME}-${PYTHON_VERSION}.tar"
                            }
                        }
                    }
                }
            }
        }
        stage("Push images") {
            when {
                expression { currentBuild.currentResult == 'SUCCESS' }
            }
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.10', '3.11', '3.12', '3.13'
                    }
                    axis {
                        name 'DOCKER_REGISTRY'
                        values 'harbor2', 'dockerhub'
                    }
                }
                stages {
                    stage("Push") {
                        steps {
                            script {
                                echo "Push docker image for ${PYTHON_VERSION} on registry ${DOCKER_REGISTRY}"
                                unstash "${PROJECT_NAME}-${PYTHON_VERSION}.tar"
                                def output = sh(script: "docker load -i ${PROJECT_NAME}-${PYTHON_VERSION}.tar",  returnStdout: true).trim()
                                def (imgName, imgTags) = output.tokenize(" ")[-1].tokenize(":")
                                dockerRepository.pushImage(
                                    imgName: imgName,
                                    imgTags: imgTags,
                                    registryType: "${DOCKER_REGISTRY}",
                                    isLatest: env.PYTHON_VERSION == "3.13" ? true : false
                                )
                            }
                        }
                    }
                }
            }
        }
        stage("Update docker description") {
            when {
                expression { currentBuild.currentResult == 'SUCCESS' }
            }
            matrix {
                axes {
                    axis {
                        name 'DOCKER_REGISTRY'
                        values 'harbor2', 'dockerhub'
                    }
                }
                stages {
                    stage("Update description") {
                        agent {
                            docker {
                                label 'jenkins-node-label-1' 
                                image 'chko/docker-pushrm:1'
                                args '-v ${WORKSPACE}:/myvol '
                            }
                        }
                        steps {
                            script {
                                echo "Update project description on registry ${DOCKER_REGISTRY}"
                                dockerRepository.updateReadMe(
                                    srcImg: dockerImg,
                                    registryType: "${DOCKER_REGISTRY}",
                                )
                            }
                        }
                    }
                }
            }
        }
    }
    post {
        always {
            echo 'Cleaning up Docker images...'
            sh 'docker system prune -af || true'
        }
    }
}
