# -*- coding: utf-8 -*-
__all__ = ('GCovCoverageInstrumenter',)


INSTRUMENTATION = (
    "/* DARJEELING :: INSTRUMENTATION :: START */\n"
    "#include <stdio.h>\n"
    "#include <stdlib.h>\n"
    "#include <signal.h>\n"
    "#ifdef __cplusplus\n"
    "  extern \"C\" void __gcov_flush(void);\n"
    "#else\n"
    "  void __gcov_flush(void);\n"
    "#endif\n"
    "void darjeeling_sighandler(int sig){\n"
    "  __gcov_flush();\n"
    "  if(sig != SIGUSR1 && sig != SIGUSR2)\n"
    "    exit(1);\n"
    "}\n"
    "void darjeeling_ctor (void) __attribute__ ((constructor));\n"
    "void darjeeling_ctor (void) {\n"
    "  struct sigaction new_action;\n"
    "  new_action.sa_handler = darjeeling_sighandler;\n"
    "  sigemptyset(&new_action.sa_mask);\n"
    "  new_action.sa_flags = 0;\n"
    "  sigaction(SIGTERM, &new_action, NULL);\n"
    "  sigaction(SIGINT, &new_action, NULL);\n"
    "  sigaction(SIGKILL, &new_action, NULL);\n"
    "  sigaction(SIGSEGV, &new_action, NULL);\n"
    "  sigaction(SIGFPE, &new_action, NULL);\n"
    "  sigaction(SIGBUS, &new_action, NULL);\n"
    "  sigaction(SIGILL, &new_action, NULL);\n"
    "  sigaction(SIGABRT, &new_action, NULL);\n"
    "  /* Use signal for SIGUSR to remove handlers */\n"
    "  signal(SIGUSR1, darjeeling_sighandler);\n"
    "  signal(SIGUSR2, darjeeling_sighandler);\n"
    "}\n"
    "/* DARJEELING :: INSTRUMENTATION :: END */\n"
)


class GCovCoverageInstrumenter(CoverageInstrumenter):
    @attr.s(frozen=True, auto_attribs=True)
    class Instructions:
        files_to_instrument: Set[str]

        @staticmethod
        def from_dict(d: Dict[str, Any]) -> 'Instructions':
            return

    @classmethod
    def from_instructions(cls, instructions: Instructions) -> 'GCovCoverageInstrumenter':
        return

    def instrument(self, container: ProgramContainer) -> None:
        pass
