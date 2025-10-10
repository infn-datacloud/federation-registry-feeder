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

    triggers {
        cron("${dockerRepository.periodicTrigger(env.BRANCH_NAME)}")
    }

    stages {
        stage('Create and push images') {
            parallel {
                stage('Image with python 3.10 published on Harbor') {
                    steps {
                        githubNotify context: 'build', status: 'PENDING', description: 'Build started'
                        script {
                            dockerRepository.buildAndPushImage(
                                imageName: "${PROJECT_NAME}",
                                dockerfile: "${DOCKERFILE}",
                                registryType: 'harbor2',
                                pythonVersion: '3.10'
                            )
                        }
                        githubNotify context: 'test', status: 'SUCCESS', description: 'Build successful'
                    }
                }
                stage('Image with python 3.11 published on Harbor') {
                    steps {
                        script {
                            dockerRepository.buildAndPushImage(
                                imageName: "${PROJECT_NAME}",
                                dockerfile: "${DOCKERFILE}",
                                registryType: 'harbor2',
                                pythonVersion: '3.11'
                            )
                        }
                    }
                }
                stage('Image with python 3.12 published on Harbor') {
                    steps {
                        script {
                            dockerRepository.buildAndPushImage(
                                imageName: "${PROJECT_NAME}",
                                dockerfile: "${DOCKERFILE}",
                                registryType: 'harbor2',
                                pythonVersion: '3.12'
                            )
                        }
                    }
                }
                stage('Image with python 3.13 published on Harbor') {
                    steps {
                        script {
                            dockerRepository.buildAndPushImage(
                                imageName: "${PROJECT_NAME}",
                                dockerfile: "${DOCKERFILE}",
                                registryType: 'harbor2',
                                pythonVersion: '3.13',
                                isLatest: true
                            )
                        }
                    }
                }
                stage('Image with python 3.10 published on DockerHub') {
                    steps {
                        script {
                            dockerRepository.buildAndPushImage(
                                imageName: "${PROJECT_NAME}",
                                dockerfile: "${DOCKERFILE}",
                                registryType: 'dockerhub',
                                pythonVersion: '3.10'
                            )
                        }
                    }
                }
                stage('Image with python 3.11 published on DockerHub') {
                    steps {
                        script {
                            dockerRepository.buildAndPushImage(
                                imageName: "${PROJECT_NAME}",
                                dockerfile: "${DOCKERFILE}",
                                registryType: 'dockerhub',
                                pythonVersion: '3.11'
                            )
                        }
                    }
                }
                stage('Image with python 3.12 published on DockerHub') {
                    steps {
                        script {
                            dockerRepository.buildAndPushImage(
                                imageName: "${PROJECT_NAME}",
                                dockerfile: "${DOCKERFILE}",
                                registryType: 'dockerhub',
                                pythonVersion: '3.12'
                            )
                        }
                    }
                }
                stage('Image with python 3.13 published on DockerHub') {
                    steps {
                        script {
                            dockerRepository.buildAndPushImage(
                                imageName: "${PROJECT_NAME}",
                                dockerfile: "${DOCKERFILE}",
                                registryType: 'dockerhub',
                                pythonVersion: '3.13',
                                isLatest: true
                            )
                        }
                    }
                }
            }
        }
    }
}
