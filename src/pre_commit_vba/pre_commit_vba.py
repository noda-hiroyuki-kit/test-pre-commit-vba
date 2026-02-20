"""pre-commit-vba script.

extract code files from excel workbook with codes.
"""

# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "pywin32>=311",
#   "typer>=0.23.1",
# ]
# ///
import re
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from logging import INFO, basicConfig, getLogger
from pathlib import Path
from typing import Annotated
from zipfile import ZipFile

import typer
from win32com.client import DispatchEx

__version__ = "0.0.2"


class UndefineTypeError(Exception):
    """Custom UndefineTypeError exception."""


class NotReleaseBranchError(Exception):
    """Custom NotReleaseBranch exception."""


class InvalidSemVerError(Exception):
    """Custom InvalidSemVer exception."""


@dataclass(frozen=True)
class Constants:
    """Constants Class for win32com.

    This class can replace win32com.client.constants as follows:
    `constants=Constants()`
    """

    vbext_ct_ClassModule: int = 2  # from enum vbext_ComponentType  # noqa: N815
    vbext_ct_Document: int = 100  # from enum vbext_ComponentType  # noqa: N815
    vbext_ct_MSForm: int = 3  # from enum vbext_ComponentType  # noqa: N815
    vbext_ct_StdModule: int = 1  # from enum vbext_ComponentType  # noqa: N815


class SettingsCommonFolder:
    """Settings for handling common folder."""

    def __init__(
        self,
        workbook_path: Path,
        folder_suffix: str,
    ) -> None:
        """Initialize settings."""
        self.__workbook_path = workbook_path
        self.__folder_suffix = folder_suffix

    @property
    def common_folder(self) -> Path:
        """Return common folder path."""
        return Path(
            self.__workbook_path.parent,
            f"{self.__workbook_path.name.split('.')[0]}{self.__folder_suffix}",
        )

    @property
    def workbook_path(self) -> Path:
        """Return workbook path."""
        return self.__workbook_path


class SettingsFoldersHandleExcel:
    """Settings for handling Excel."""

    def __init__(
        self,
        settings_common_folder: SettingsCommonFolder,
        export_folder: str,
        custom_ui_folder: str,
        code_folder: str,
    ) -> None:
        """Initialize settings."""
        self.__settings_common_folder = settings_common_folder
        self.__export_folder = export_folder
        self.__custom_ui_folder = custom_ui_folder
        self.__code_folder = code_folder

    @property
    def export_folder(self) -> Path:
        """Return common folder path."""
        return Path(self.__settings_common_folder.common_folder, self.__export_folder)

    @property
    def custom_ui_folder(self) -> Path:
        """Return custom UI folder path."""
        return Path(
            self.__settings_common_folder.common_folder, self.__custom_ui_folder
        )

    @property
    def code_folder(self) -> Path:
        """Return code folder path."""
        return Path(self.__settings_common_folder.common_folder, self.__code_folder)

    @property
    def workbook_path(self) -> Path:
        """Return workbook path."""
        return self.__settings_common_folder.workbook_path

    @property
    def common_folder(self) -> Path:
        """Return common folder path."""
        return self.__settings_common_folder.common_folder


class SettingsOptionsHandleExcel:
    """Settings for handling Excel options."""

    def __init__(
        self, *, enable_folder_annotation: bool, create_gitignore: bool
    ) -> None:
        """Initialize settings."""
        self.__enable_folder_annotation = enable_folder_annotation
        self.__create_gitignore = create_gitignore

    def enable_folder_annotation(self) -> bool:
        """Return enable folder annotation setting."""
        return self.__enable_folder_annotation

    def create_gitignore(self) -> bool:
        """Return create gitignore setting."""
        return self.__create_gitignore


class ExcelVbaExporter:
    """A placeholder class for ExcelVbaExporter."""

    def __init__(self, settings: SettingsFoldersHandleExcel) -> None:
        """Initialize with file path."""
        self.__app = self.__get_xl_app()
        self.__workbook = self.__app.Workbooks.Open(
            settings.workbook_path, ReadOnly=True
        )
        settings.export_folder.mkdir(parents=True, exist_ok=True)
        for vb_comp in self.__workbook.VBProject.VBComponents:
            vb_comp_file_name = vb_component_type_factory(
                vb_comp.Name, vb_comp.Type
            ).file_name
            vb_comp.Export(Path(settings.export_folder, f"{vb_comp_file_name}"))

    def __get_xl_app(self) -> DispatchEx:
        """Get Excel application."""
        excel_app = DispatchEx("Excel.Application")
        excel_app.Visible = True
        excel_app.DisplayAlerts = False
        return excel_app

    def __del__(self) -> None:
        """Destructor to close workbook and quit app."""
        try:
            self.__workbook.Close(SaveChanges=False)
            self.__app.Quit()
        except Exception:
            logger.exception("Error in destructor")
            raise


def vb_component_type_factory(module_name: str, type_id: int) -> IVbComponentType:
    """Return VbComponentType instances."""
    if type_id == constants.vbext_ct_StdModule:
        return StdModule(module_name)
    if type_id == constants.vbext_ct_ClassModule:
        return ClassModule(module_name)
    if type_id == constants.vbext_ct_MSForm:
        return UserFormModule(module_name)
    if type_id == constants.vbext_ct_Document:
        return SheetClassModule(module_name)
    raise UndefineTypeError(type_id)


class IVbComponentType(ABC):
    """A placeholder class for VbComponentType constants."""

    def __init__(self, module_name: str) -> None:
        """Initialize Class Module type."""
        self.module_name = module_name

    @property
    @abstractmethod
    def file_name(self) -> str:
        """Return module name."""
        raise NotImplementedError


class StdModule(IVbComponentType):
    """Standard Module type."""

    @property
    def file_name(self) -> str:
        """Return module name."""
        return self.module_name + ".bas"


class ClassModule(IVbComponentType):
    """Class Module type."""

    @property
    def file_name(self) -> str:
        """Return module name."""
        return self.module_name + ".cls"


class UserFormModule(IVbComponentType):
    """User Form type."""

    @property
    def file_name(self) -> str:
        """Return module name."""
        return self.module_name + ".frm"


class SheetClassModule(IVbComponentType):
    """Sheet class type."""

    @property
    def file_name(self) -> str:
        """Return module name."""
        return self.module_name + ".cls"


class ExcelCustomUiExtractor:
    """A placeholder class for ExcelCustomUiExtractor."""

    def __init__(self, settings: SettingsFoldersHandleExcel) -> None:
        """Initialize with file path."""
        self.__settings = settings
        self.__extract_custom_ui_files()

    def __extract_custom_ui_files(self) -> None:
        self.__settings.custom_ui_folder.mkdir(parents=True, exist_ok=True)
        self.__extract_custom_ui_file("customUI/customUI14.xml")
        self.__extract_custom_ui_file("customUI/customUI.xml")

    def __extract_custom_ui_file(self, full_item_name: str) -> None:
        try:
            with ZipFile(self.__settings.workbook_path, "r") as zip_ref:
                file_data = zip_ref.read(full_item_name)
            with Path(self.__settings.custom_ui_folder, Path(full_item_name).name).open(
                mode="wb"
            ) as xml_file:
                xml_file.write(file_data)
        except KeyError:
            logger.info(
                "%s does not exists in %s",
                Path(full_item_name).name,
                self.__settings.workbook_path.name,
            )


class Utf8Converter:
    """A placeholder class for Utf8Converter."""

    def __init__(
        self, settings: SettingsFoldersHandleExcel, options: SettingsOptionsHandleExcel
    ) -> None:
        """Initialize with file path."""
        self.__settings = settings
        self.__options = options
        self.__add_gitignore_file()
        self.__convert_to_utf8()

    def __add_gitignore_file(self) -> None:
        if not self.__options.create_gitignore():
            return
        gitignore_content = f"{self.__settings.export_folder.name}/\n"
        with Path(self.__settings.common_folder, ".gitignore").open(
            mode="w", encoding="utf-8", newline="\n"
        ) as gitignore_file:
            gitignore_file.write(gitignore_content)

    def __convert_to_utf8(self) -> None:
        for file_path in self.__settings.export_folder.glob("*.*"):
            if self.__is_binary(file_path):
                continue
            text_before_trailing_ws_removal = self.__format_line_breaks(
                file_path.read_text(encoding="shift-jis")
            )
            content = self.__remove_trailing_white_space_in_vba_metadata_portion(
                text_before_trailing_ws_removal
            )
            code_folder = self.__get_code_folder(content)
            code_folder.mkdir(parents=True, exist_ok=True)
            code_path = Path(code_folder, file_path.name)
            code_path.write_text(content, encoding="utf-8", newline="\n")

    def __format_line_breaks(self, text: str) -> str:
        return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"

    def __remove_trailing_white_space_in_vba_metadata_portion(self, text: str) -> str:
        remover = self._trailing_white_space_class_factory(text)
        return remover.remove_trailing_white_space(text)

    def _trailing_white_space_class_factory(
        self, text: str
    ) -> ITrailingWhiteSpaceRemover:
        if re.search(r"^VERSION 5", text):
            return FrxModuleTrailingWhiteSpaceRemover()
        return OtherModuleTrailingWhiteSpaceRemover()

    def __get_code_folder(self, text: str) -> Path:
        code_root_folder = self.__settings.code_folder
        if not self.__options.enable_folder_annotation():
            return code_root_folder
        pattern = r"\'@(F|f)older(\s|\()\"(.*)\"((.*)|\))(.*)\n"
        if match := re.search(pattern, text):
            return Path(code_root_folder, *match.group(3).split("."))
        return code_root_folder

    def __is_binary(self, file_path: Path, chunk_size: int = 1024) -> bool:
        try:
            with Path.open(file_path, "rb") as f:
                chunk = f.read(chunk_size)
                return b"\x00" in chunk
        except OSError:
            return False


class ITrailingWhiteSpaceRemover(ABC):
    """A placeholder class for TrailingWhiteSpaceRemover."""

    @abstractmethod
    def remove_trailing_white_space(self, text: str) -> str:
        """Remove trailing white space in VBA metadata portion."""
        raise NotImplementedError


class FrxModuleTrailingWhiteSpaceRemover(ITrailingWhiteSpaceRemover):
    """A placeholder class for FrxModuleTrailingWhiteSpaceRemover."""

    def remove_trailing_white_space(self, text: str) -> str:
        """Remove trailing white space in VBA metadata portion."""
        content_split = text.split("\n")
        pattern = (
            r"^(VERSION 5|Begin|"
            r"\s*(Caption|Client|OleObject|StartUp)|"
            r"End|Attribute VB_)"
        )
        continue_flag = True
        for content_index, content in enumerate(content_split):
            if not continue_flag:
                break
            if re.search(pattern, content):
                content_split[content_index] = content.rstrip()
                continue
            continue_flag = False
        return "\n".join(content_split)


class OtherModuleTrailingWhiteSpaceRemover(ITrailingWhiteSpaceRemover):
    """A placeholder class for OtherModuleTrailingWhiteSpaceRemover."""

    def remove_trailing_white_space(self, text: str) -> str:
        """Remove trailing white space in VBA metadata portion."""
        return text


def add_to_staging(settings: SettingsFoldersHandleExcel) -> None:
    """Add files extracted to staging."""
    process = subprocess.Popen(  # noqa: S603
        ["git", "add", settings.common_folder],  # noqa: S607
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout_data, stderr_data = process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout_data, stderr_data = process.communicate()  # noqa: RUF059


def get_version_from_branch_name() -> str:
    """Get version from branch name."""
    branch_name = get_current_branch_name()
    check_valid_branch_name(branch_name)
    return get_and_check_version_from_branch_name(branch_name)


def check_valid_branch_name(branch_name: str) -> None:
    """Check valid branch name."""
    branch_name_header = "release/v"
    if not branch_name.startswith(branch_name_header):
        raise NotReleaseBranchError(branch_name)


def get_and_check_version_from_branch_name(branch_name: str) -> str:
    """Get and check version from branch name."""
    sem_ver_pattern = (
        r"(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)"
        r"\.(?P<patch>0|[1-9]\d*)"
        r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
        r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))"
        r"?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )
    match = re.search(sem_ver_pattern, branch_name)
    if match:
        return match.group(0)
    raise InvalidSemVerError(branch_name)


def get_current_branch_name() -> str:
    """Get current branch name."""
    process = subprocess.Popen(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],  # noqa: S607
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout_data, stderr_data = process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout_data, stderr_data = process.communicate()  # noqa: RUF059
    return stdout_data.decode("utf-8").replace("\n", "")


def get_workbook_version(workbook_path: Path) -> str:
    """Get workbook version."""
    app = DispatchEx("Excel.Application")
    app.Visible = False
    app.DisplayAlerts = False
    workbook = app.Workbooks.Open(workbook_path, ReadOnly=True)
    try:
        version = str(workbook.BuiltinDocumentProperties("Document version"))
    finally:
        workbook.Close(SaveChanges=False)
        app.Quit()
    return version


app = typer.Typer()
basicConfig(level=INFO)
logger = getLogger(__name__)
constants = Constants()


def version_callback(value: bool) -> None:  # noqa: FBT001
    """Print version information."""
    if value:
        typer.echo(f"pre-commit-vba version: {__version__}")
        raise typer.Exit


@app.command("extract")
def extract_vba_code_from_workbooks(  # noqa: PLR0913
    *,
    target_path: Annotated[str, typer.Option()] = ".",
    folder_suffix: Annotated[str, typer.Option()] = ".VBA",
    export_folder: Annotated[str, typer.Option()] = "export",
    custom_ui_folder: Annotated[str, typer.Option()] = "customUI",
    code_folder: Annotated[str, typer.Option()] = "code",
    version: Annotated[  # noqa: ARG001
        bool | None, typer.Option("--version", callback=version_callback, is_eager=True)
    ] = None,
    enable_folder_annotation: Annotated[
        bool, typer.Option("--enable-folder-annotation/--disable-folder-annotation")
    ] = True,
    create_gitignore: Annotated[
        bool, typer.Option("--create-gitignore/--not-create-gitignore")
    ] = True,
) -> None:
    """Extract VBA code from Excel workbooks."""
    logger.debug("Target path: %s", str(Path(target_path).resolve()).lower())
    logger.debug("folder-suffix: %s", folder_suffix)
    logger.debug("export-folder: %s", export_folder)
    logger.debug("custom-ui-folder: %s", custom_ui_folder)
    logger.debug("code-folder: %s", code_folder)
    logger.debug("enable-folder-annotation: %s", enable_folder_annotation)
    logger.debug("create-gitignore: %s", create_gitignore)
    options = SettingsOptionsHandleExcel(
        enable_folder_annotation=enable_folder_annotation,
        create_gitignore=create_gitignore,
    )
    for workbook_path in Path(target_path).resolve().glob("*.xls*"):
        if workbook_path.name.startswith("~$"):
            continue
        common_folder_settings = SettingsCommonFolder(
            workbook_path=workbook_path,
            folder_suffix=folder_suffix,
        )
        folder_settings = SettingsFoldersHandleExcel(
            settings_common_folder=common_folder_settings,
            export_folder=export_folder,
            custom_ui_folder=custom_ui_folder,
            code_folder=code_folder,
        )
        if folder_settings.common_folder.exists():
            shutil.rmtree(folder_settings.common_folder)
        ExcelVbaExporter(folder_settings)
        ExcelCustomUiExtractor(folder_settings)
        Utf8Converter(folder_settings, options)
        add_to_staging(folder_settings)


@app.command()
def check(
    *,
    target_path: Annotated[str, typer.Option()] = ".",
    version: Annotated[  # noqa: ARG001
        bool | None, typer.Option("--version", callback=version_callback, is_eager=True)
    ] = None,
) -> None:
    """Check between workbook version and repository name."""
    try:
        exist_workbook: bool = False
        for workbook_path in Path(target_path).resolve().glob("*.xls*"):
            if workbook_path.name.startswith("~$"):
                continue
            exist_workbook = True
            workbook_version = get_workbook_version(workbook_path)
            branch_version = get_version_from_branch_name()
            if workbook_version != "v" + branch_version:
                logger.error(
                    "Version mismatch: Workbook version '%s' != Branch version '%s'",
                    workbook_version,
                    branch_version,
                )
                sys.exit(1)
        if not exist_workbook:
            logger.warning("No Excel workbooks found in the target path.")
            sys.exit(0)
    except NotReleaseBranchError:
        logger.info("Not a release branch")
        sys.exit(0)
    except InvalidSemVerError:
        logger.exception("Invalid semantic version in branch name")
        sys.exit(1)
    logger.info("Version check passed.")


if __name__ == "__main__":
    app()
