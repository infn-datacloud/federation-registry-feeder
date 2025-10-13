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
        SRC_DIR = 'src'
        POETRY_VERSION = '2.1'
        TARGET_PYTHON = '3.13'
    }

    triggers {
        cron("${myCron.periodicTrigger(env.BRANCH_NAME)}")
    }

    stages {
        stage('Linting and format') {
            agent {
                docker {
                    label 'jenkins-node-label-1'
                    image "python:${env.TARGET_PYTHON}"
                    args '-u root:root'
                    reuseNode true
                }
            }
            when {
                expression { return env.CHANGE_ID != null } // It is a PR
            }
            steps {
                script {
                    ruffChecks()
                }
            }
        }
        stage('Tests execution') {
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.10', '3.11', '3.12', '3.13'
                    }
                }
                stages {
                    stage('Test'){
                        agent {
                            docker {
                                label 'jenkins-node-label-1'
                                image "python:${env.PYTHON_VERSION}"
                                args '-u root:root'
                                reuseNode true
                            }
                        }
                        stages{
                            stage('Install dependencies') {
                                steps {
                                    script  {
                                        installDependencies()
                                    }
                                }
                            }
                            stage('Run Tests') {
                                steps {
                                    script {
                                        runTests()
                                    }
                                }
                                post {
                                    always {
                                        script {
                                            archiveArtifacts artifacts: 'coverage-reports/**/*', fingerprint: true
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        stage('Combine coverages') {
            agent {
                docker {
                    label 'jenkins-node-label-1'
                    image "python:${env.TARGET_PYTHON}"
                    args '-u root:root'
                    reuseNode true
                }
            }
            steps {
                script {
                    combineCovReports()
                }
            }
            post {
                success {
                    script {
                        archiveArtifacts artifacts: 'coverage.xml', fingerprint: true
                    }
                }
            }
        }
        stage('Notify SonarCloud') {
            agent {
                docker {
                    label 'jenkins-node-label-1'
                    image 'sonarsource/sonar-scanner-cli'
                    args "-u root:root -v ${env.WORKSPACE}:/usr/src"
                    reuseNode true
                }
            }
            steps {
                script {
                    notifySonar()
                }
            }
        }
        stage('Build images') {
            when {
                allOf {
                    expression { return currentBuild.currentResult != 'UNSTABLE' }
                    expression { return currentBuild.result != 'UNSTABLE' }
                    expression { return env.CHANGE_ID != null || env.TAG_NAME != null } // It is a PR or tag
                }
            }
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.10', '3.11', '3.12', '3.13'
                    }
                }
                stages {
                    stage('Build') {
                        steps {
                            script {
                                buildDockerImage()
                            }
                        }
                    }
                }
            }
        }
        stage('Push images') {
            when {
                allOf {
                    expression { return currentBuild.currentResult != 'UNSTABLE' }
                    expression { return currentBuild.result != 'UNSTABLE' }
                    expression { return env.CHANGE_ID != null || env.TAG_NAME != null } // It is a PR or tag
                }
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
                    stage('Push') {
                        steps {
                            script {
                                pushDockerImage(
                                    isLatest: env.PYTHON_VERSION == env.TARGET_PYTHON ? true : false
                                )
                            }
                        }
                    }
                }
            }
        }
        stage('Update docker description') {
            when {
                allOf {
                    expression { return currentBuild.currentResult != 'UNSTABLE' }
                    expression { return currentBuild.result != 'UNSTABLE' }
                    expression { return env.CHANGE_ID != null || env.TAG_NAME != null } // It is a PR or tag
                }
            }
            matrix {
                axes {
                    axis {
                        name 'DOCKER_REGISTRY'
                        values 'harbor2', 'dockerhub'
                    }
                }
                stages {
                    stage('Update description') {
                        steps {
                            script {
                                updateDockerRegistryDoc()
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
