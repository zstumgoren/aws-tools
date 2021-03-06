#!/usr/bin/env python
"""
Library for working with S3 buckets.
"""
import os
import sys

import boto
from boto.s3.connection import S3Connection
from boto.s3.key import Key


def percent_cb(complete, total):
    """A simple file upload/download status function."""
    sys.stdout.write('.')
    sys.stdout.flush()

class S3(object):
    """
    Provides a persistent connection to S3 and methods for interacting with buckets.
    
    USAGE:

    # Set your AWS credentials
    AWS_ACCESS_KEY_ID='<your_access_id>'
    AWS_SECRET_KEY='<your_access_key>'

    # Create an s3 connection
    conn = S3(AWS_ACCESS_KEY_ID, AWS_SECRET_KEY)
    
    # Sync a local directory and S3 bucket name
    conn.sync_local_dir_to_bucket('/my/local/dir', 's3-bucket-name') 
    
    """
    
    def __init__(self, AWS_ACCESS_KEY_ID, AWS_SECRET_KEY):
        if not AWS_ACCESS_KEY_ID or not AWS_SECRET_KEY:
            sys.exit("You must provide an AWS access key and id to connect to S3.") 
        self.aws_access_key_id = AWS_ACCESS_KEY_ID
        self.aws_secret_key = AWS_SECRET_KEY
        self.conn = S3Connection(self.aws_access_key_id, self.aws_secret_key)

    def sync_local_dir_to_bucket(self, directory, bucket_name):
        """
        One-way synchronization of local files and S3 bucket. Uploads
        any files that are on local but not on S3.

        Required arguments are the full path to a local directory, and the 
        name of an S3 bucket.
        """
        try:
            bucket = self.conn.get_bucket(bucket_name)
        except boto.exception.S3ResponseError, e:
            sys.exit("""
                    An error occurred retrieving the S3 bucket named '%s' 
                    Are you sure the bucket exists and you spelled it correctly?
                    Below is full error response from S3:\n\n %s
                    """ % (bucket_name, e))

        keys = self.get_s3_filenames(bucket)
        base_path, local_files = self.get_local_filenames(directory)

        # Get local files not found on s3
        missing_on_s3 = local_files - keys

        if not missing_on_s3:
            sys.exit("Files in %s are synchronized with S3. Nothing uploaded." % base_path)
        
        print "Files found locally that are not on S3."
        for fname in missing_on_s3:
            key = Key(bucket)
            key.key = fname
            target_file = os.path.join(base_path, fname) 
            print "Uploading %s to S3 bucket %s" % (target_file, bucket_name)
            key.set_contents_from_filename(target_file, cb=percent_cb, num_cb=10) 
            print


    def get_s3_filenames(self, bucket):
        """Returns all keys for a bucket. Requires a bucket instance."""
        return set([key.name for key in bucket.list()])

    def get_local_filenames(self, directory):
        """
        Returns a tuple containing the path to a directory 
        of files targeted for upload to S3, along with a set 
        of filenames from that target directory.

        Example:

            ('/home/user/Desktop', 
             set([
                 'AP_FTP_DATA/AK/dbready/AK_Candidate.txt',
                 'AP_FTP_DATA/AK/dbready/AK_Race.txt',
             ...])
            )
             
        """
        files = set([])
        
        base = os.path.dirname(directory.rstrip('/'))

        for dirpath, dirnames, filenames in os.walk(directory):
            # S3 has no concept of directories. To preserve directory structure of files
            # inside some toplevel directory, we strip the base path from filenames.
            path = dirpath.split(base + '/')[-1]
            for filename in filenames:
                files.add(os.path.join(path, filename))

        return base, files
        
