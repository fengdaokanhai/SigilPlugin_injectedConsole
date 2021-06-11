#!/bin/sh
PROJDIR=`dirname "$0"`
CURDIR=`pwd`

cd $PROJDIR

if [ -f $PROJDIR/VERSION ];
then
    VERSION=`cat $PROJDIR/VERSION`
else
    VERSION=latest
fi

function createpack() {
    local file=$1/injectedConsole_$VERSION.zip
    if zip -q -r $file injectedConsole/
    then
        echo "Create a package file located in \n\t$file"
    else
        return 1
    fi
}

createpack $CURDIR || createpack $HOME || createpack $PROJDIR || echo Cannot create package file
cd $CURDIR
