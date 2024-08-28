void pushImage(String srcImage, String targetImageName, String registryUrl, String registryCredentials) {
    // Login to target registry, retrieve docker image and push it to the registry
    sh "docker tag ${srcImage} ${targetImageName}"
    docker.withRegistry("${registryUrl}", "${registryCredentials}") {
        if ("${BRANCH_NAME}" == 'main') {
            docker.image("${targetImageName}").push('main')
            docker.image("${imageName}").push('latest')
        }
        docker.image("${targetImageName}").push("${BRANCH_NAME}")
        docker.image("${targetImageName}").push("${COMMIT_SHA}")
    }
}

void updateReadMe(String provider, String imageName, String registryUser, String registryPassword, String registryHost) {
    // Login to target registry, retrieve docker image and push it to the registry
    sh """docker run --rm \
        -v ${WORKSPACE}:/myvol \
        -e DOCKER_USER=${registryUser} \
        -e DOCKER_PASS=${registryPassword} \
        chko/docker-pushrm:1 \
        --provider ${provider} \
        --file /myvol/README.md \
        --debug \
        ${registryHost}/${imageName}
        """
}


pipeline {
    agent {
        node { label 'jenkinsworker00' }
    }

    environment {
        PROJECT_NAME = 'federation-registry-feeder'

        DOCKER_HUB_CREDENTIALS_NAME = 'docker-hub-credentials'
        DOCKER_HUB_CREDENTIALS = credentials("${DOCKER_HUB_CREDENTIALS_NAME}")
        DOCKER_HUB_ORGANIZATION = 'indigopaas'
        DOCKER_HUB_URL = 'https://index.docker.io/v1/'

        HARBOR_CREDENTIALS_NAME = 'harbor-paas-credentials'
        HARBOR_CREDENTIALS = credentials("${HARBOR_CREDENTIALS_NAME}")
        HARBOR_ORGANIZATION = 'datacloud-middleware'
        HARBOR_URL = 'https://harbor.cloud.infn.it'

        BRANCH_NAME = "${env.BRANCH_NAME != null ? env.BRANCH_NAME : 'jenkins'}"
        COMMIT_SHA = sh(returnStdout: true, script: 'git rev-parse --short=10 HEAD').trim()
    }

    stages {
        stage('Build docker image') {
            steps {
                script {
                    docker.build("${PROJECT_NAME}", '-f ./Dockerfile .')
                }
            }
        }
        stage('Push to registries') {
            parallel {
                stage('Harbor') {
                    steps {
                        script {
                            pushImage(
                                "${PROJECT_NAME}",
                                "${HARBOR_ORGANIZATION}/${PROJECT_NAME}",
                                "${HARBOR_URL}",
                                "${HARBOR_CREDENTIALS_NAME}",
                            )
                            updateReadMe(
                                'harbor2',
                                "${HARBOR_ORGANIZATION}/${PROJECT_NAME}",
                                '${HARBOR_CREDENTIALS_USR}',
                                '${HARBOR_CREDENTIALS_PSW}',
                                'harbor.cloud.infn.it',
                            )
                        }
                    }
                }
                stage('DockerHub') {
                    steps {
                        script {
                            pushImage(
                                "${PROJECT_NAME}",
                                "${DOCKER_HUB_ORGANIZATION}/${PROJECT_NAME}",
                                "${DOCKER_HUB_URL}",
                                "${DOCKER_HUB_CREDENTIALS_NAME}",
                            )
                            updateReadMe(
                                'dockerhub',
                                "${DOCKER_HUB_ORGANIZATION}/${PROJECT_NAME}",
                                '${DOCKER_HUB_CREDENTIALS_USR}',
                                '${DOCKER_HUB_CREDENTIALS_PSW}',
                                'docker.io',
                            )
                        }
                    }
                }
            }
        }

        stage('Remove docker images') {
            steps {
                sh "docker rmi ${PROJECT_NAME}"
            }
        }
    }
}
