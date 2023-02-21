import select
import socket
import sys
import queue
import time
import re
import os

def serve_client(sock, info):
    
    bad_request = "HTTP/1.0 400 Bad Request\r\n".encode()
    not_found = "HTTP/1.0 404 Not Found\r\n".encode()
    success = "HTTP/1.0 200 OK\r\n".encode()
    response = ""
    
    #get the request and the header if it exists
    request_line,header = info.split('\n', 1)
    
    #if second line is random text remove it
    if "Connection" not in header:
        header = ""
    
    #separate the requestline to each invididual component
    try:
        get, page, http = request_line.split()
    
    #if not possible then print the bad request and close the socket
    except:
        response = "HTTP/1.0 400 Bad Request\r\n"
        sock.send(bad_request)
        print("{}: {} {} {}".format(time.strftime("%a %b %d %X %Z %Y", time.localtime()),
                                str(sock.getsockname()[0] + ":" + str(sock.getsockname()[1])),
                                "",
                                response + header + "\r\n\r\n"))
        return "close"
    
    # check if it is in the right format and look for if it is successful or non-existent
    if get == 'GET' and http == 'HTTP/1.0':
        filename = page[1:]
        #read successful
        try:
            with open(filename, 'r') as file:
                content = file.read()
                response = "HTTP/1.0 200 OK\r\n"
             
                sock.send(success)
                sock.send(content.encode())
                sock.send("\r\n".encode())
        #cannot find the specified file
        except:
            response = "HTTP/1.0 404 Not Found\r\n"
            sock.send(not_found)
    # if in the wrong format send bad request
    else:
        response = "HTTP/1.0 400 Bad Request\r\n"
        sock.send(bad_request)
        print("{}: {} {} {}".format(time.strftime("%a %b %d %X %Z %Y", time.localtime()),
                                str(sock.getsockname()[0] + ":" + str(sock.getsockname()[1])),
                                "",
                                response + header + "\r\n\r\n"))
        return "close"
    # print if it is in the right format and is either successful or not found
    print("{}: {} {} {}".format(time.strftime("%a %b %d %X %Z %Y", time.localtime()),
                                str(sock.getsockname()[0] + ":" + str(sock.getsockname()[1])),
                                request_line.strip(),
                                response + header + "\r\n\r\n"))
    #check header and return the connection type
    if "keep-alive" in header:
        return "keep-alive"
    else:
        return "close"

#set up the python server
def start_server(host, port):
    
    #set up server variables
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setblocking(0)
    server.bind((host, port))
    server.listen(5)

    inputs = [server]
    outputs = []
    message_queues = {}
    request_message = {}
    timeout = 30
    
    while inputs:
        
        readable, writable, exceptional = select.select(inputs, outputs, inputs, timeout)
        
        for sock in readable:
            if sock is server:
                connection, client_address = server.accept()
                connection.setblocking(0)
                inputs.append(connection)
                request_message[connection] = ""
                message_queues[connection] = queue.Queue()
                
            else:
                sock.settimeout(timeout)
                try:
                    message1 =  sock.recv(1024).decode()
                except:
                    sock.send('Timeout\n')
                if message1:
                    request_message[sock] = request_message[sock] + message1
                    message = request_message[sock]
                    sock.settimeout(None)
                    #wait for the 2 new lines before taking the data in the queue
                    if message[-2:] != '\n\n':
                        continue
                    
                    #determine the type of connection and the request
                    connection = serve_client(sock, request_message[sock])
                    if connection == "close":
                        inputs.remove(sock)
                        sock.close()
                        del request_message[sock]
                        
                    #resets the request message to empty (believe this is why the txt file doesn't work)
                    if connection == "keep-alive":
                        request_message[sock] = ""
                        if sock not in outputs:
                            outputs.append(sock)
                else:
                    inputs.remove(sock)
                    sock.close()
                    del request_message[sock]
                    
        for sock in writable:
            try:
                next_msg = message_queues[sock].get_nowait()
            except queue.Empty:
                outputs.remove(sock)
                if sock not in inputs:
                    sock.close()
                    del message_queues[sock]
                    del request_message[sock]
                    
        for sock in exceptional:
            inputs.remove(sock)
            sock.close()
            del message_queues[sock]
            del request_message[sock]
    #attempt to timeout (should be working)
        if sock not in readable and writable and exceptional:
            sock.close()
    if not (readable or writable or exceptional):
        for sock in request_message:
            sock.close()
        
if __name__ == '__main__':
    start_server(sys.argv[1], int(sys.argv[2]))



