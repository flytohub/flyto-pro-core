# Contract Overrides

JSON files here add or replace module contracts after the Flyto2 Core catalog is
loaded. Files are parsed off the async event loop; invalid entries are logged and
excluded rather than partially registered.
