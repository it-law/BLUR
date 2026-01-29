; 🔐 BLUR - Document Privacy Masking Tool
; NSIS Installer Script v1.0
;
; This script creates a Windows installer for BLUR Portable Edition
; Requirements: NSIS (https://nsis.sourceforge.io/)
;
; To build:
; 1. Install NSIS
; 2. Right-click this file → Compile NSIS Script
; 3. Wait for compilation
; 4. Result: BLUR_Installer_v1.0.exe in current directory

!include "MUI2.nsh"
!include "x64.nsh"

; ============================================================================
; Defines
; ============================================================================

!define PRODUCT_NAME "BLUR"
!define PRODUCT_DESCRIPTION "Document Privacy Masking Tool"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "BLUR Development Team"
!define PRODUCT_WEB_SITE "https://github.com/blur"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; Installation folder
InstallDir "$PROGRAMFILES64\${PRODUCT_NAME}"

; ============================================================================
; Settings
; ============================================================================

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "BLUR_Setup_v${PRODUCT_VERSION}.exe"
CRCCheck on
BrandingText "${PRODUCT_NAME} v${PRODUCT_VERSION}"

; Require admin rights
RequestExecutionLevel admin

; ============================================================================
; MUI Settings
; ============================================================================

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "Russian"

; ============================================================================
; Installer Sections
; ============================================================================

Section "Install"
    
    ; Check if running on 64-bit system
    ${If} ${RunningX64}
        SetRegView 64
    ${Else}
        MessageBox MB_ICONEXCLAMATION "BLUR требует Windows 64-bit!"
        Abort
    ${EndIf}
    
    ; Set output path to installation folder
    SetOutPath "$INSTDIR"
    
    ; Extract files from dist folder
    File /r "dist\*.*"
    
    ; Create Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\START_BLUR.bat"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Stop ${PRODUCT_NAME}.lnk" "$INSTDIR\STOP_BLUR.bat"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall.lnk" "$INSTDIR\uninstall.exe"
    
    ; Create desktop shortcut
    CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\START_BLUR.bat"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Write registry entries
    ${If} ${RunningX64}
        SetRegView 64
    ${EndIf}
    
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME} ${PRODUCT_VERSION}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\BLUR.exe"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
    
SectionEnd

; ============================================================================
; Uninstaller Section
; ============================================================================

Section "Uninstall"
    
    ; Kill running process
    taskkill /IM BLUR.exe /F
    
    ; Remove Start Menu shortcuts
    RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"
    
    ; Remove desktop shortcut
    Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
    
    ; Remove installation directory
    RMDir /r "$INSTDIR"
    
    ; Remove registry entries
    ${If} ${RunningX64}
        SetRegView 64
    ${EndIf}
    
    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
    
SectionEnd

; ============================================================================
; Functions
; ============================================================================

Function .onInit
    ; Check if BLUR is already running
    FindProcDLL::FindProc "BLUR.exe"
    ${If} $R0 = 1
        MessageBox MB_ICONWARNING "BLUR уже запущен!$\nПожалуйста, закройте BLUR перед установкой."
        Abort
    ${EndIf}
    
    ; Ensure running as admin
    Call IsAdmin
    ${If} $R0 = 0
        MessageBox MB_ICONEXCLAMATION "Этот инсталлятор требует прав администратора!"
        SetErrorLevel 740
        Quit
    ${EndIf}
FunctionEnd

Function IsAdmin
    GetCurrentUser $R0
    IfErrors NotAdmin
    Pop $0
    IfErrors NotAdmin
    StrCpy $R0 1
    Goto Done
    
    NotAdmin:
        StrCpy $R0 0
    Done:
FunctionEnd

Function .onInstSuccess
    MessageBox MB_ICONINFORMATION "BLUR успешно установлен!$\n$\nВыбери для открытия приложения:"
    ExecShell "open" "$INSTDIR\START_BLUR.bat"
FunctionEnd

; ============================================================================
; End of Script
; ============================================================================
