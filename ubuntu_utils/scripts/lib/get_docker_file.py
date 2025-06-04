#!/usr/bin/env python3
import io
import os
import stat as stat_module
import tarfile
from pathlib import Path

import click
import docker
import docker.errors


def copy_from_image(
    image_name: str, image_src_path: str | Path, local_dest_base_dir: str | Path
) -> None:
    client = docker.from_env()  # Initialize Docker client from environment variables
    container = None
    try:
        # Ensure the local destination directory exists before extraction
        try:
            os.makedirs(local_dest_base_dir, exist_ok=True)
        except OSError as e:
            click.echo(
                f"Failed to create local directory '{local_dest_base_dir}': {e}",
                err=True,
            )
            raise click.Abort() from e  # Abort if directory creation fails

        # Try to create a container from the specified image
        try:
            click.echo(
                f"Attempting to create a container using image '{image_name}'..."
            )
            container = client.containers.create(image_name)
        except docker.errors.ImageNotFound:
            # If image not found locally, try pulling from remote registry
            click.echo(
                f"Image '{image_name}' not found locally. Attempting to pull from remote registry...",
                err=True,
            )
            try:
                client.images.pull(image_name)
                click.echo(
                    f"Successfully pulled image '{image_name}'. Retrying container creation..."
                )
                container = client.containers.create(image_name)
            except docker.errors.ImageNotFound as e:
                click.echo(
                    f"Error: Image '{image_name}' not found after pulling.", err=True
                )
                raise click.Abort() from e
            except docker.errors.APIError as pull_or_create_error:
                click.echo(
                    f"Error while pulling or creating container from image '{image_name}': {pull_or_create_error}",
                    err=True,
                )
                raise click.Abort() from pull_or_create_error

        # Get the archive (tar stream) and file metadata from the specified path inside the container
        click.echo(
            f"Getting archive from '{image_src_path}' in container {container.short_id}..."
        )
        bits, stat_info = container.get_archive(image_src_path)

        # Determine if the path inside image is a directory by checking file mode bits
        is_dir_in_image = stat_module.S_ISDIR(stat_info["mode"])
        archive_root_name = stat_info[
            "name"
        ]  # Top-level directory or filename in the tar archive

        click.echo(f"Extracting archive to '{local_dest_base_dir}'...")
        # Use BytesIO to wrap the binary stream for tarfile to process
        with (
            io.BytesIO(b"".join(bits)) as tar_stream,
            tarfile.open(fileobj=tar_stream, mode="r") as tar,
        ):
            # Iterate over all members (files/directories) in the tar archive
            for member in tar.getmembers():
                original_member_name = (
                    member.name
                )  # Save original member name for logging/restoration
                current_member_path_in_tar = member.name

                if is_dir_in_image:
                    # For directory archives, remove the top-level directory prefix from member names
                    if current_member_path_in_tar.startswith(archive_root_name + "/"):
                        member.name = current_member_path_in_tar[
                            len(archive_root_name) + 1 :
                        ]
                    elif current_member_path_in_tar == archive_root_name:
                        # Skip the top-level directory itself
                        continue
                    else:
                        raise AssertionError(
                            f"Unexpected archive member '{original_member_name}' "
                            f"in directory archive '{archive_root_name}'."
                        )

                if not member.name:
                    raise AssertionError(
                        f"Eempty member name (original: '{original_member_name}')."
                    )

                # Safely extract the member to the local destination directory
                # Using filter='data' for secure extraction (prevents directory traversal attacks)
                tar.extract(member, path=local_dest_base_dir, filter="data")

                # Restore original member name in case it's used later
                member.name = original_member_name

        # Success message
        click.echo(
            click.style(
                f"Successfully copied '{image_src_path}' "
                f"from image '{image_name}' to local directory '{local_dest_base_dir}'.",
                fg="green",
            )
        )

    finally:
        if container:
            # Clean up temporary container to free resources
            click.echo(f"Removing temporary container {container.short_id}...")
            container.remove(force=True)


@click.command()
@click.argument("image_name", type=str)
@click.argument("image_src_path", type=click.Path())
@click.argument("local_dst_base_dir", type=click.Path())
def cli(image_name: str, image_src_path: str, local_dst_base_dir: str):
    copy_from_image(image_name, image_src_path, local_dst_base_dir)


if __name__ == "__main__":
    cli()
