.. title:: nmrglue-ng

.. raw:: html

   <main class="ng-home">
     <section class="ng-hero" aria-labelledby="ng-hero-title">
       <div class="ng-hero-copy">
         <p class="ng-eyebrow">NMR data in Python</p>
         <h1 id="ng-hero-title">nmrglue-ng</h1>
         <p class="ng-hero-lede">
           Read, write, convert, process, and analyse NMR data with the
           scientific Python tools you already use.
          </p>
          <div class="ng-actions">
            <a class="ng-button ng-button-primary" href="install.html">Install <span aria-hidden="true">→</span></a>
            <a class="ng-button ng-button-secondary" href="getting-started/index.html">Get started <span aria-hidden="true">→</span></a>
            <a class="ng-button ng-button-secondary" href="tutorials/index.html">Explore tutorials</a>
          </div>
       </div>
        <div class="ng-terminal" aria-label="Installation and import example">
          <div class="ng-terminal-bar" aria-hidden="true"><span></span><span></span><span></span></div>
          <pre><span class="ng-prompt">$</span> uv add nmrglue-ng&#10;&#10;<span class="ng-code-keyword">import</span> nmrglue <span class="ng-code-keyword">as</span> ng&#10;dic, data = ng.pipe.read(<span class="ng-code-string">"spectrum.ft2"</span>)</pre>
          <img class="ng-terminal-spectrum" src="_static/home-fid.svg" alt="">
       </div>
     </section>

     <section class="ng-section" aria-labelledby="ng-capabilities-title">
       <h2 class="ng-eyebrow" id="ng-capabilities-title">One toolkit, complete workflows</h2>
       <div class="ng-feature-grid">
        <a class="ng-feature ng-feature-wide" href="tutorials/reading.html">
           <span class="ng-feature-index">01</span>
           <span class="ng-feature-copy"><strong>Read and write</strong><span>Work with NMRPipe, Bruker, Agilent/Varian, Sparky, and other established NMR formats.</span></span>
           <span class="ng-feature-arrow" aria-hidden="true">↗</span>
         </a>
        <a class="ng-feature" href="how-to/processing.html">
           <span class="ng-feature-index">02</span>
           <span class="ng-feature-copy"><strong>Process</strong><span>Build transparent pipelines with apodization, transforms, phasing, and baseline tools.</span></span>
           <span class="ng-feature-arrow" aria-hidden="true">↗</span>
         </a>
        <a class="ng-feature" href="how-to/conversion.html">
           <span class="ng-feature-index">03</span>
           <span class="ng-feature-copy"><strong>Convert</strong><span>Move data between supported formats while keeping acquisition metadata close at hand.</span></span>
           <span class="ng-feature-arrow" aria-hidden="true">↗</span>
         </a>
        <a class="ng-feature ng-feature-wide ng-feature-accent" href="how-to/quantification.html">
           <span class="ng-feature-index">04</span>
           <span class="ng-feature-copy"><strong>Analyse</strong><span>Combine peak picking, integration, lineshape fitting, and unit-aware axes with NumPy and SciPy.</span></span>
           <span class="ng-feature-arrow" aria-hidden="true">↗</span>
         </a>
       </div>
     </section>

     <section class="ng-section ng-paths" aria-labelledby="ng-paths-title">
       <h2 class="ng-eyebrow" id="ng-paths-title">Choose your path</h2>
       <div class="ng-path-grid">
         <a class="ng-path" href="getting-started/index.html">
           <span class="ng-path-label">New to nmrglue-ng?</span>
           <strong>Start with installation</strong>
           <span>Set up the package, confirm the compatible import, and find your first workflow.</span>
           <b>Getting started <span aria-hidden="true">→</span></b>
         </a>
         <a class="ng-path" href="tutorials/index.html">
           <span class="ng-path-label">Learn by doing</span>
           <strong>Follow executable tutorials</strong>
           <span>Read file structures, inspect metadata, create axes, and plot spectra step by step.</span>
           <b>View tutorials <span aria-hidden="true">→</span></b>
         </a>
         <a class="ng-path" href="reference/index.html">
           <span class="ng-path-label">Know what you need?</span>
           <strong>Go to the API reference</strong>
           <span>Browse modules, functions, parameters, return values, and links to source code.</span>
           <b>Browse the API <span aria-hidden="true">→</span></b>
         </a>
       </div>
     </section>

     <section class="ng-project" aria-labelledby="ng-project-title">
       <div><p class="ng-eyebrow">Open source and independent</p><h2 id="ng-project-title">A new version of nmrglue</h2></div>
       <p>nmrglue-ng continues the historical project with an emphasis on compatibility, scientific correctness, reproducibility, and careful modernization.</p>
       <div class="ng-project-actions">
         <a class="ng-button ng-button-light" href="about/index.html">About the project <span aria-hidden="true">→</span></a>
         <a class="ng-project-link" href="about/contributors.html">History &amp; contributors <span aria-hidden="true">→</span></a>
       </div>
     </section>
   </main>

.. toctree::
    :hidden:
    :maxdepth: 2

    getting-started/index
    whats-new
    tutorials/index
    how-to/index
    jbnmr_examples/index
    reference/index
    glossary/index
    contribute/index
    about/index
