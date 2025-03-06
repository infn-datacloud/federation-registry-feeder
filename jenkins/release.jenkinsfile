@Library('jenkins-libraries') _

pipeline {
    agent {
        node { label 'jenkins-node-label-1' }
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