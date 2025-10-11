#!groovy
@Library('jenkins-libraries') _

pipeline {
    agent {
        node { label 'jenkins-node-label-1' }
    }

    environment {
        PROJECT_NAME = 'federation-registry-feeder'
        DOCKERFILE = './docker/Dockerfile'
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
                    stage("Test") {
                        steps {
                            script {
                                echo "Test on python${PYTHON_VERSION}"
                                pythonTests.testCode(pythonVersion: env.PYTHON_VERSION)
                            }
                        }
                    }
                    stage("Build docker image") {
                        steps {
                            script {
                                echo "Build docker image for python${PYTHON_VERSION}"
                                dockerImg = dockerRepository.buildImage(
                                    imageName: env.PROJECT_NAME,
                                    dockerfile: env.DOCKERFILE,
                                    pythonVersion: env.PYTHON_VERSION
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
