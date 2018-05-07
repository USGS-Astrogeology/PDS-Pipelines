#!/usgs/apps/anaconda/bin/python

import subprocess


class HPCjob(object):
    """

    Attributes
    ----------
    jobstring : str
    name : str
    array : str
    cmd : str
    Sout : str
    Serror : str
    Wall : str
    module : str
    path : str
    partition : str
    memory : str
    """
    def __init__(self):

        self.jobstring = "#!/bin/bash"
        self.name = ''
        self.array = ''
        self.cmd = ''
        self.Sout = ''
        self.Serror = ''
        self.Wall = ''
        self.module = ''
        self.path = ''
        self.partition = ''
        self.memory = ''

    def setJobName(self, name):
        """
        Concatenates strings

        Adds 'name' to the string "#SBATCH -J "

        Parameters
        ----------
        name : str
        """

        self.name = "#SBATCH -J " + name

    def setJobArray(self, number):
        """
        Concatenates strings

        Converts 'number' to a string an concatenates it with 
        "#SBATCH --array=1-"

        Parameters
        ----------
        number : int
        """
        self.array = "#SBATCH --array=1-" + str(number)

    def setCommand(self, cmd):
        """
        Parameters
        ----------
        cmd : str
        """

        self.cmd = cmd

    def setStdOut(self, Ofile):
        """
        Concatenates strings

        Concatenates 'Ofile' and "#SBATCH --output="

        Parameters
        ----------
        Ofile : str
        """
        self.Sout = "#SBATCH --output=" + Ofile

    def setStdError(self, Efile):
        """
        Concatenates strings

        Concatenates "#SBATCH --error=" and 'Efile'

        Parameters
        ----------
        Efile : str
        """
        self.Serror = "#SBATCH --error=" + Efile

    def setWallClock(self, time):
        """
        Parameters
        ----------
        time : str
        """
        self.Wall = "#SBATCH -t " + time

    def setPartition(self, item):
        """
        Parameters
        ----------
        item : str

        """
        self.partition = "#SBATCH --partition=" + item

    def setMemory(self, item):
        """
        Parameters
        ----------
        item : str

        """
        self.memory = "#SBATCH --mem-per-cpu=" + item

    def setModule(self, item):
        """
        Parameters
        ----------
        item : str
        """
        self.module = "eval `/usr/bin/modulecmd bash load " + item + "`"

    def addPath(self, addpath):
        """
        Parameters
        ----------
        addpath : str
        """
        self.path = "export PATH=" + addpath + ":$PATH"

    def MakeJobFile(self, filename):
        """
        Parameters
        ----------
        filename
        """
        self.sbatchfile = filename

        file = open(filename, "w")

        file.write("#!/bin/bash\n")
        if self.name:
            file.write("\n" + self.name)
        if self.Sout:
            file.write("\n" + self.Sout)
        if self.Serror:
            file.write("\n" + self.Serror)
        if self.partition:
            file.write("\n" + self.partition)
        if self.array:
            file.write("\n" + self.array)
        if self.Wall:
            file.write("\n" + self.Wall)
        if self.memory:
            file.write("\n" + self.memory)

        if self.module:
            file.write("\n\n" + self.module)
            file.write("\necho `printenv PATH`")

        if self.path:
            file.write("\n\n" + self.path)
            file.write("\necho `printenv PATH`")

        if self.cmd:
            file.write("\n\n" + self.cmd)

        file.close()

    def Run(self):
        """
        Returns
        -------
        int
            result
        """
        SB = "sbatch " + str(self.sbatchfile)
        print(SB)
        print("Running sbatch")
        result = subprocess.call(SB, shell=True)

        return result
