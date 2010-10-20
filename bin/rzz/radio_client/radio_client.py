import telnetlib

QUEUE = "main_queue"
LIQUIDSOAP_BIN = "liquidsoap"

class LiquidsoapProcess():
    pass


class LiquidsoapConnection():
    def __init__(self):
        self.connection = telnetlib.Telnet('localhost', 1234, 1000)

class QueueCommandWrapper():
    queue_size = 0

    def __init__(self, connection, queue_name):
        self.connection = connection
        self.queue_name = queue_name

    def insert(self, position, uri):
        """
        Insert a source at the corresponding position into the queue
        Returns the source id
        """

        if position > self.queue_size:
            print 'You inserted beyond the queue size. uri appended at the end'

        command = '{0}.insert {1} {2} \n'.format(self.queue, position, uri)
        connection.write(command)
        response = connection.read_until('END')[:-3]
        return int(response)

    def lol(self):
        pass

    def push(self, uri):
        """
        Push a source with the corresponding uri into the queue
        Returns the source id
        """
        command = '{0}.push {1}\n'.format(self.queue, uri)
        connection.write(command)
        response = connection.read_until('END')[:-3]		
        return int(response)

    def get_queue(self):
        """
        Returns a list of the ids currently queued
        """
        connection.write('{0}.queue\n'.format(self.queue))
        response = connection.read_until('END')[:-3]
        return [int(t) for t in response.split(' ')]

    def remove(self, id):
        """
        Remove the source with given id
        """
        connection.write('{0}.remove {1}\n'.format(self.queue, id))
        response = connection.read_until('END')[:-3]
        if not response == 'OK':
            print 'There is no source with the given id'

    def move(self, id, position):
        """
        """


class ServerCommandsWrapper():
    connection = CONNECTION
    self.queue = QueueCommandWrapper(connection)
