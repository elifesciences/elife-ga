elifeLibrary {
    stage 'Checkout'
    checkout scm

    stage 'Install'
    sh './install.sh'

    stage 'Project tests'
    sh './test.sh'
}
