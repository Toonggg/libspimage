import numpy
import spimage

def array_to_image(img,msk=None):
    s = img.shape
    d = len(list(s))
    if d == 3:
        sp_img = spimage.sp_image_alloc(s[2],s[1],s[0])
    else:
        sp_img = spimage.sp_image_alloc(s[1],s[0],1)
    sp_img.image[:] = img[:]
    if msk is not None:
        sp_img.mask[:] = msk[:]
    return sp_img

def prtf(images_rs,supports,translate=True,enantio=True,full_out=False):
    s = images_rs[0].shape
    N = len(images_rs)
    S = (N,s[0],s[1])

    image0_rs = images_rs[0]
    image0_fs = numpy.fft.fftn(image0_rs)

    sp_image0_rs = array_to_image(image0_rs,supports[0])
    sp_image0_fs = array_to_image(image0_fs)

    sp_amp_fs = spimage.sp_image_duplicate(sp_image0_fs,spimage.SP_COPY_ALL)
    spimage.sp_image_dephase(sp_amp_fs)

    spimage.sp_image_free(sp_image0_rs)
    spimage.sp_image_free(sp_image0_fs)

    sum_fs = image0_fs.copy()
    tmp = abs(sum_fs) > 0.
    if tmp.sum() > 0:
        sum_fs[tmp] /= abs(sum_fs[tmp])

    sp_sum_fs = array_to_image(sum_fs)

    zeros = numpy.zeros(shape=s,dtype="int")
    zeros[tmp == False] = 1

    sp_avg_img = array_to_image(image0_rs)
    avg_msk = numpy.zeros(shape=s,dtype="float")
    
    images_rs_super = numpy.zeros(shape=S,dtype="complex128")
    images_rs_super[0,:] = image0_rs[:]
    masks_rs_super = numpy.zeros(shape=S,dtype="bool")
    masks_rs_super[0,:] = supports[0,:]

    for i,img,sup in zip(range(1,N),images_rs[1:],supports[1:]):
        # Initialize image
        sp_img = array_to_image(img,sup)
        
        # Translate and enantio matching
        if translate:
            spimage.sp_image_superimpose(sp_avg_img,sp_img,spimage.SpEnantiomorph)
            spimage.sp_image_phase_match(sp_avg_img,sp_img,2)
        spimage.sp_image_add(sp_avg_img,sp_img)

        sup_t = numpy.array(sp_img.mask,dtype="bool")
        if sup_t.sum() > 0:
            avg_msk[sup_t] += 1
        
        # Cache image and support
        images_rs_super[i,:] = sp_img.image[:]
        masks_rs_super[i,:] = sp_img.mask[:]
        
        # Add amplitudes
        sp_tmp = spimage.sp_image_fftw3(sp_img)
        sp_tmpamp = spimage.sp_image_duplicate(sp_tmp,spimage.SP_COPY_ALL)
        spimage.sp_image_dephase(sp_tmpamp);
        spimage.sp_image_add(sp_amp_fs,sp_tmpamp)
        
        # Count zeros
        positive = abs(sp_tmp.image) > 0.
        if positive.sum() > 0:
            sp_tmp.image[positive] /= abs(sp_tmp.image)[positive]
        zeros += (positive == False)
        
        spimage.sp_image_add(sp_sum_fs,sp_tmp)
        
        spimage.sp_image_free(sp_img)
        spimage.sp_image_free(sp_tmp)
        spimage.sp_image_free(sp_tmpamp)
  
    sp_prtf = spimage.sp_image_duplicate(sp_sum_fs,spimage.SP_COPY_DATA|spimage.SP_COPY_MASK)
    sp_prtf.image[:] /= N
    if zeros.sum() > 0:
        sp_prtf.image[zeros > 0] = 0.
    spimage.sp_image_dephase(sp_prtf)

    avg_img = sp_avg_img.image[:].copy()
    avg_sup = avg_msk > 0
    prtf = abs(sp_prtf.image[:]).copy()
    prtf = numpy.fft.fftshift(prtf)

    for sp_i in [sp_prtf,sp_avg_img,sp_amp_fs,sp_sum_fs]:
        spimage.sp_image_free(sp_i)  
      
    out = {}
    out["prtf"] = prtf
    out["super_image"] = avg_img
    if full_out:
        out["prtf_r"] = spimage.radial_mean(prtf,cx=s[1]/2,cy=s[0]/2)
        out["super_mask"] = avg_sup
        out["images"] = images_rs_super
        out["masks"] = masks_rs_super
    return out

detector_pixel_to_resolution_element = lambda i_pixel, pixel_size, detector_distance, wavelength: wavelength / 4. / numpy.sin( numpy.arctan2( i_pixel * pixel_size, detector_distance ) / 2. )
