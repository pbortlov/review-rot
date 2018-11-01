import os
import logging
import gitlab
import datetime
from reviewrot.basereview import BaseService, BaseReview
from gitlab.exceptions import GitlabGetError
from distutils.version import LooseVersion
from basereview import  LastComment

log = logging.getLogger(__name__)


class GitlabService(BaseService):
    """
    This class represents Gitlab. The reference can be found here:
     https://docs.gitlab.com/ee/api/
    """
    def request_reviews(self, user_name, repo_name=None, state_=None,
                        value=None, duration=None, last_commented=None, token=None, host=None,
                        ssl_verify=True, **kwargs):
        """
        Creates a gitlab object.
        Requests merge requests for specified username and repo name.
        If repo name is not provided then requests merge requests
        for all repos for specified username/organization.

        Args:
            user_name (str): Gitlab namespace
            repo_name (str): Gitlab project name for specified
                          namespace
            state_ (str): The state for pull requests, e.g, older
                        or newer
            value (int): The value in terms of duration for requests
                         to be older or newer than
            duration (str): The duration in terms of period(year, month,
                            hour, minute) for requests to be older or
                            newer than
            token (str): Gitlab token for authentication
            host (str): Gitlab host name for authentication
            ssl_verify (bool/str): Whether or not to verify SSL certificates,
                                   or a path to a CA file to use.
        Returns:
            response (list): Returns the list of pull requests for
                             specified user(group) name and projectname or all
                             projectname for given groupname
        """
        gl = gitlab.Gitlab(host, token, ssl_verify=ssl_verify)

        # Test GitLab version and fall back to API v3 if possible, as a
        # workaround to 404 Errors produced by authentication on some
        # GitLab instances
        try:
            gl_version = gl.version()
        except ValueError:
            # Some instances have thrown a ValueError instead of failing
            # gracefully when queried for version
            gl_version = ('unknown', 'unknown')
        if (gl_version == ('unknown', 'unknown') or
           LooseVersion(gl_version[0]) < LooseVersion('9.0')):
            # GitLab API v3 was deprecated in GitLab v9.0
            gl = gitlab.Gitlab(host, token, ssl_verify=ssl_verify,
                               api_version=3)

        gl.auth()
        log.debug('Gitlab instance created: %s', gl)
        response = []
        # if Repository name is explicitly provided
        if repo_name is not None:
            try:
                # get project object for given repo_name(project name)
                project = gl.projects.get(os.path.join(user_name, repo_name))
            except GitlabGetError:
                log.exception('Project %s not found for user %s',
                              repo_name, user_name)
                raise Exception('Project %s not found for user %s'
                                % (repo_name, user_name))
            # get merge requests for specified username and project name
            res = self.get_reviews(uname=user_name, project=project,
                                   state_=state_, value=value,
                                   duration=duration, last_commented=last_commented)
            # extend in case of a non empty result
            if res:
                response.extend(res)

        else:
            # get user object
            groups = gl.groups.search(user_name)
            if not groups:
                log.debug('Invalid user/group name: %s', user_name)
                raise Exception('Invalid user/group name: %s' % user_name)

            # get merge requests for all projects for specified group
            for group in groups:
                projects = gl.group_projects.list(group_id=group.id)
                if not projects:
                    log.debug("No projects found for user/group name %s",
                              user_name)
                for project in projects:
                    res = self.get_reviews(uname=user_name, project=project,
                                           state_=state_, value=value,
                                           duration=duration, last_commented=last_commented)
                # extend in case of a non empty result
                if res:
                    response.extend(res)
        return response

    def get_reviews(self, uname, project, state_=None,
                    value=None, duration=None, last_commented=None):
        """
        Fetches merge requests for specified username(groupname)
        and repo(project) name.
        Formats the merge requests details and print it on console.

        Args:
            user_name (str): Gitlab namespace
            repo_name (str): Gitlab project name for specified
                             namespace
            state_ (str): The state for pull requests, e.g, older
                        or newer
            value (str): The value in terms of duration for requests
                         to be older or newer than
            duration (str): The duration in terms of period(year, month,
                            hour, minute) for requests to be older or
                            newer than.

        Returns:
            res_ (list): Returns list of pull requests for specified
                         user(group) name and project name
        """
        log.debug('Looking for merge requests for %s -> %s',
                  uname, project.name)

        # get list of open merge requests for a given repository(project)
        merge_requests = project.mergerequests.list(project_id=project.id,
                                                    state='opened')
        if not merge_requests:
            log.debug('No open merge requests found for %s/%s ',
                      uname, project.name)
        res_ = []
        for mr in merge_requests:


            last_comment = self.get_last_comment(mr)

            try:
                mr_date = datetime.datetime.strptime(
                    mr.created_at, '%Y-%m-%dT%H:%M:%S.%fZ')

            except ValueError:
                mr_date = datetime.datetime.strptime(
                    mr.created_at, '%Y-%m-%dT%H:%M:%SZ')

            """ check if review request is older/newer than specified time
            interval"""
            result = self.check_request_state(mr_date, state_, value, duration)

            if result is False:
                log.debug("merge request '%s' is not %s than specified"
                          " time interval", mr.title, state_)
                continue

            if last_comment and last_commented:
                if self.has_new_comments(last_comment.created_at, last_commented):
                    log.debug("merge request '%s' has new comments  in last %s days", mr.title, last_commented)
                    continue



            res = GitlabReview(user=mr.author['username'],
                               title=mr.title,
                               url=mr.web_url,
                               time=mr_date,
                               comments=mr.user_notes_count,
                               # XXX - I don't know how to find gitlab avatars
                               # for now.  Can we figure this out later?
                               image=GitlabReview.logo,
                               last_comment=last_comment,
                               project_name=project.name,
                               project_url =project.web_url)

            log.debug(res)
            res_.append(res)
        return res_


    def get_last_comment(self, mr):
        mr_notes = mr.notes.list()
        for note in mr_notes:
            if note.system == False:
                return LastComment(author=note.author['username'], body=note.body,
                                    created_at=datetime.datetime.strptime(
                                    note.created_at, '%Y-%m-%dT%H:%M:%S.%fZ'))


class GitlabReview(BaseReview):
    # XXX - Here just until we figure out how to do gitlab avatars.
    logo = 'https://docs.gitlab.com/assets/images/gitlab-logo.svg'
    pass
