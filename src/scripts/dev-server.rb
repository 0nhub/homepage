#!/usr/bin/env ruby
# Minimal static server that reads files into memory (no sendfile).
# Needed because macOS sandbox blocks WEBrick's sendfile syscall.
require "socket"
require "uri"

ROOT = File.expand_path(ARGV[0] || ".")
PORT = Integer(ARGV[1] || 8765)
HOST = ARGV[2] || "127.0.0.1"

TYPES = {
  ".html" => "text/html; charset=utf-8",
  ".css" => "text/css; charset=utf-8",
  ".js" => "application/javascript; charset=utf-8",
  ".json" => "application/json; charset=utf-8",
  ".png" => "image/png",
  ".jpg" => "image/jpeg",
  ".jpeg" => "image/jpeg",
  ".gif" => "image/gif",
  ".svg" => "image/svg+xml",
  ".webp" => "image/webp",
  ".ico" => "image/x-icon",
  ".mp4" => "video/mp4",
  ".txt" => "text/plain; charset=utf-8",
  ".xml" => "application/xml",
  ".woff" => "font/woff",
  ".woff2" => "font/woff2"
}

def safe_path(request_path)
  path = URI.decode_www_form_component(request_path.split("?", 2).first)
  path = "/index.html" if path == "/"
  full = File.expand_path(File.join(ROOT, path))
  return nil unless full.start_with?(ROOT)
  if File.directory?(full)
    return nil unless path.end_with?("/")
    full = File.join(full, "index.html")
  end
  File.file?(full) ? full : nil
end

server = TCPServer.new(HOST, PORT)
$stdout.sync = true
puts "Serving #{ROOT} on http://#{HOST}:#{PORT}/"

loop do
  socket = server.accept
  Thread.new(socket) do |client|
    begin
      request = client.gets
      next unless request
      method, raw_path, = request.split(" ")
      while (line = client.gets)
        break if line == "\r\n" || line == "\n"
      end

      if method != "GET" && method != "HEAD"
        body = "Method not allowed"
        client.print "HTTP/1.1 405 Method Not Allowed\r\nContent-Type: text/plain\r\nContent-Length: #{body.bytesize}\r\nConnection: close\r\n\r\n"
        client.print body unless method == "HEAD"
        next
      end

      unless raw_path.end_with?("/")
        dir = File.expand_path(File.join(ROOT, URI.decode_www_form_component(raw_path.split("?", 2).first)))
        if File.directory?(dir)
          client.print "HTTP/1.1 301 Moved Permanently\r\nLocation: #{raw_path.split("?", 2).first}/\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
          next
        end
      end

      file = safe_path(raw_path)
      unless file
        body = "Not found"
        client.print "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nContent-Length: #{body.bytesize}\r\nConnection: close\r\n\r\n"
        client.print body unless method == "HEAD"
        next
      end

      data = File.binread(file)
      type = TYPES[File.extname(file).downcase] || "application/octet-stream"
      client.print "HTTP/1.1 200 OK\r\nContent-Type: #{type}\r\nContent-Length: #{data.bytesize}\r\nConnection: close\r\n\r\n"
      client.write(data) unless method == "HEAD"
    rescue Errno::EPIPE, Errno::ECONNRESET
      # client gone
    ensure
      client.close
    end
  end
end
