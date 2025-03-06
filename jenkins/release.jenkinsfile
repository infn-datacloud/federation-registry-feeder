@Library('jenkins-libraries') _

pipeline {
    agent {
        node { label 'jenkins-node-label-1' }
    }

    environment {
        GH_TOKEN = credentials('github-app-infn-datacloud')
    }

    stages {
        stage('Release') {
            steps {
                script {
                    nodejs(nodeJSInstallationName: 'Default') {
                        sh 'npx semantic-release --debug'
                    }
                }
            }
        }
    }
}