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
                    image "python:${TARGET_PYTHON}"
                    args '-u root:root'
                    reuseNode true
                }
            }
            when {
                expression { return env.CHANGE_ID != null } // It is a PR
            }
            steps {
                script {
                    linting.ruff(srcDir: env.SRC_DIR)
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
                                image "python:${PYTHON_VERSION}"
                                args '-u root:root'
                                reuseNode true
                            }
                        }
                        stages{
                            stage('Install dependencies') {
                                steps {
                                    script  {
                                        pythonTests.installDependecies()
                                    }
                                }
                            }
                            stage('Run Tests') {
                                steps {
                                    script {
                                        echo "Running tests on python${PYTHON_VERSION}"
                                        configFileProvider([configFile(fileId: '.coveragerc', variable: 'COVERAGERC')]) {
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
                    image "python:${TARGET_PYTHON}"
                    args '-u root:root'
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
                    args "-u root:root -v ${WORKSPACE}:/usr/src"
                    reuseNode true
                }
            }
            steps {
                withSonarQubeEnv('SonarCloud') {
                    echo 'Sends coverage report to SonarCloud'
                    sh """
                        sonar-scanner \
                        -D sonar.projectKey=${ORG_NAME}_${PROJECT_NAME} \
                        -D sonar.organization=${ORG_NAME} \
                        -D sonar.sources=${SRC_DIR} \
                        -D sonar.tests=tests \
                        -D sonar.branch.name=${BRANCH_NAME} \
                        -D sonar.python.coverage.reportPaths=coverage.xml
                    """
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
                                echo "Push docker image for ${PYTHON_VERSION} on registry ${DOCKER_REGISTRY}"
                                unstash "${PROJECT_NAME}-${PYTHON_VERSION}.tar"
                                def output = sh(script: "docker load -i ${PROJECT_NAME}-${PYTHON_VERSION}.tar",  returnStdout: true).trim()
                                def (imgName, imgTags) = output.tokenize(" ")[-1].tokenize(":")
                                dockerRepository.pushImage(
                                    imgName: imgName,
                                    imgTags: imgTags,
                                    registryType: "${DOCKER_REGISTRY}",
                                    isLatest: env.PYTHON_VERSION == "${TARGET_PYTHON}" ? true : false
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
                                echo "Update project description on registry ${DOCKER_REGISTRY}"
                                dockerRepository.updateReadMe(
                                    imgName: env.PROJECT_NAME,
                                    registryType: "${DOCKER_REGISTRY}"
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
