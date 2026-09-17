OUTPUT_FORMAT("elf32-littlearm", "elf32-bigarm", "elf32-littlearm")
OUTPUT_ARCH(arm)
ENTRY(gcc_entry)
SECTIONS
{
  . = SEGMENT_START("text-segment", 0) + SIZEOF_HEADERS;
  .hash : { *(.hash) }
  .gnu.hash : { *(.gnu.hash) }
  .dynsym : { *(.dynsym) }
  .dynstr : { *(.dynstr) }
  .rel.dyn : { *(.rel.init) *(.rel.text .rel.text.*) *(.rel.rodata .rel.rodata.*) *(.rel.data .rel.data.*) *(.rel.got) *(.rel.bss .rel.bss.*) *(.rel.iplt) }
  .rela.dyn : { *(.rela.init) *(.rela.text .rela.text.*) *(.rela.rodata .rela.rodata.*) *(.rela.data .rela.data.*) *(.rela.got) *(.rela.bss .rela.bss.*) *(.rela.iplt) }
  .rel.plt : { *(.rel.plt) }
  .rela.plt : { *(.rela.plt) }
  .init : { KEEP(*(.init)) } =0
  .plt : { *(.plt) }
  .iplt : { *(.iplt) }
  .text : { *(.text.unlikely .text.*_unlikely) *(.text .stub .text.* .gnu.linkonce.t.*) *(.glue_7t) *(.glue_7) *(.vfp11_veneer) *(.v4_bx) } =0
  .fini : { KEEP(*(.fini)) } =0
  PROVIDE(__etext = .); PROVIDE(_etext = .); PROVIDE(etext = .);
  .rodata : { *(.rodata .rodata.* .gnu.linkonce.r.*) }
  .ARM.extab : { *(.ARM.extab* .gnu.linkonce.armextab.*) }
  PROVIDE_HIDDEN(__exidx_start = .);
  .ARM.exidx : { *(.ARM.exidx* .gnu.linkonce.armexidx.*) }
  PROVIDE_HIDDEN(__exidx_end = .);
  .init_array : { PROVIDE_HIDDEN(__init_array_start = .); KEEP(*(SORT(.init_array.*))) KEEP(*(.init_array)) PROVIDE_HIDDEN(__init_array_end = .); }
  .fini_array : { KEEP(*(SORT(.fini_array.*))) KEEP(*(.fini_array)) }
  .data.rel.ro : { *(.data.rel.ro.local* .gnu.linkonce.d.rel.ro.local.*) *(.data.rel.ro* .gnu.linkonce.d.rel.ro.*) }
  .dynamic : { *(.dynamic) }
  .got : { *(.got.plt) *(.igot.plt) *(.got) *(.igot) }
  .data : { __data_start = .; *(.data .data.* .gnu.linkonce.d.*) SORT(CONSTRUCTORS) }
  _edata = .; PROVIDE(edata = .); __bss_start = .; __bss_start__ = .;
  .bss : { *(.dynbss) *(.bss .bss.* .gnu.linkonce.b.*) *(COMMON) . = ALIGN(. != 0 ? 4 : 1); }
  _bss_end__ = .; __bss_end__ = .; . = ALIGN(4); __end__ = .; _end = .; PROVIDE(end = .);
  .comment 0 : { *(.comment) }
  .ARM.attributes 0 : { KEEP(*(.ARM.attributes)) KEEP(*(.gnu.attributes)) }
  /DISCARD/ : { *(.note.GNU-stack) *(.gnu_debuglink) *(.gnu.lto_*) }
}
