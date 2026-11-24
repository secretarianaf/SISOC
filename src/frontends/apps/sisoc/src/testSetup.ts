import { configure } from "@testing-library/dom";

// The full sisoc suite runs many jsdom files in parallel; under that load the
// default 1 s wait of findBy*/waitFor is not enough and different tests time
// out on each run. A wider wait keeps assertions identical, only slower to fail.
configure({ asyncUtilTimeout: 5000 });
