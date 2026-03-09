def quick(iter):
    if len(iter)<=1:
        return iter
    else:
        pivot=iter.pop()
        
    iter_less=[]
    iter_more=[]
    for i in iter:
        if i<pivot:
            iter_less.append(i)
        else:
            iter_more.append(i)
            
    return quick(iter_less)+[pivot]+quick(iter_more)
    
a=[2,1,4,2,5,3,9,0,5]
print(quick(a))