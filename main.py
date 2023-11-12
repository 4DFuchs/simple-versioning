from git import Repo
from git.refs.tag import TagReference
import click
import semver
import logging
import sys

def find_previous_versions(git_repo: Repo, version_prefix: str, version_suffix: str):
  references = git_repo.references

  previous_versions = set()
  all_git_tags = set()

  for ref in references:
    if type(ref) == TagReference:
      ref_name = ref.name
      all_git_tags.add(ref_name)
      if ref_name is not None:
        if ref_name.startswith(version_prefix) and ref_name.endswith(version_suffix):
          extracted_version = ref_name.replace(version_prefix, '').replace(version_suffix, '')
          try:
            version = semver.Version.parse(extracted_version)
          except Exception as e:
            logging.warning(f'Tagname {ref_name} could not be parsed as <Major>.<Minor>.<Patch> Version')
          else:
            previous_versions.add(version)
            logging.info(f"Tag %s found" % ref.name)
  return previous_versions, all_git_tags

def filter_versions(versions, filter_major_version, filter_minor_version):
  if filter_major_version is None:
    return versions

  filtered_versions = set()

  for version in versions:
    if version.major == int(filter_major_version):
      if filter_minor_version is None or version.minor == int(filter_minor_version):
       filtered_versions.add(version)

  return filtered_versions


def fetch_and_pull_remotes(git_repo):
  for remote in git_repo.remotes:
    logging.info(f"Found remote {remote}")
    remote.fetch()
    remote.pull()

def push_new_tags_to_remotes(git_repo, new_tag):
  for remote in git_repo.remotes:
    logging.info(f'Found remote {remote}')
    remote.push(new_tag)

def generate_version_name(increased_version, version_prefix, version_suffix, override_patch_version, patch_version=None):
  if override_patch_version and (patch_version is not None and patch_version.strip() != ""):
    return f'{version_prefix}{increased_version.major}.{increased_version.minor}-SNAPSHOT{version_suffix}'
  else:
    return f'{version_prefix}{increased_version}{version_suffix}'


@click.command()
@click.option('--repoPath', 'repo_path', default='.', help='Path to Git-Repo')
@click.option('--versionPrefix', 'version_prefix', default='v', help='Prefix of Version')
@click.option('--versionSuffix', 'version_suffix', default='', help='Suffix of Version')
@click.option('--filterMajorVersion', 'filter_major_version', default=None, help='Only look at Major Version x', type=int)
@click.option('--filterMinorVersion', 'filter_minor_version', default=None, help='Only look at Minor Version y. (Has to be used together with Major-Filter)', type=int)
@click.option('--createNoGitTag', 'create_no_git_tag', default=False, flag_value=True, help='Creates new Tag in given Git-Repo')
@click.option('--pullBefore', 'pull_before', default=True, help='Fetch and pull before genearting Tag')
@click.option('--createSnapshotVersion', 'create_snapshot_version', flag_value=True, help='Creates Version, but Patch will stay on SNAPSHOT')
@click.option('--verbose', 'verbose', flag_value=True, help='Will print Log-Messages to stderr')
def calculate_new_version(repo_path, version_prefix, version_suffix, filter_major_version, filter_minor_version, create_no_git_tag, pull_before, create_snapshot_version, verbose):

  logging.basicConfig(stream=sys.stderr,encoding='utf-8', level=logging.INFO if verbose else logging.ERROR, format='%(levelname)s: %(message)s')

  repo = Repo(repo_path)

  if pull_before:
    fetch_and_pull_remotes(repo)

  versions, all_git_tags = find_previous_versions(repo, version_prefix, version_suffix)
  filtered_versions = filter_versions(versions, filter_major_version, filter_minor_version)

  increased_version = None

  if len(versions) == 0:
    # No Versions found. So this could be an init commit
    increased_version = semver.Version(1, 0, 0)

  elif len(filtered_versions) == 0:
    # No Version for filter found. So this could be a new version
    major = filter_major_version
    minor = filter_minor_version if filter_minor_version else 0
    increased_version = semver.Version(major, minor, 0)

  else:
    # Previous version found. To increase patch part
    max_version = max(filtered_versions)

    increased_version = max_version.bump_patch()


    logging.info(f'Max Version is {max_version}')

  new_version_tag_name = generate_version_name(increased_version, version_prefix, version_suffix, create_snapshot_version, "SNAPSHOT")

  if not create_no_git_tag:
    if new_version_tag_name in all_git_tags:
      logging.error(f'Could not create {new_version_tag_name} git-tag, because it already exsists')
      sys.exit(1)
    else:
      new_tag = repo.create_tag(new_version_tag_name)
      push_new_tags_to_remotes(repo, new_tag)

  print(new_version_tag_name)

if __name__ == '__main__':
  calculate_new_version()
