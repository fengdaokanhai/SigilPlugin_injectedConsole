#!/bin/sh
PROJDIR=`dirname "$0"`
PROJNAME=injectedConsole
CURDIR=`pwd`

cd $PROJDIR

if [ -f $PROJDIR/VERSION ]
then
    VERSION=`cat $PROJDIR/VERSION`
else
    VERSION=latest
fi

createpack() {
    local file=$1/${PROJNAME}_${VERSION}.zip
    if zip -q -r $file $PROJNAME
    then
        echo "Create a package file located in \n\t$file"
    else
        return 1
    fi
}

createpack $CURDIR || createpack $HOME || createpack $PROJDIR || echo Cannot create package file
cd $CURDIR
